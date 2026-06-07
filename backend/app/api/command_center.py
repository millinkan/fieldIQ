"""
Command Center API — Delta Dashboard endpoints.
Powers Layer 1 (delta grid), Layer 2 (decomposition), and Layer 3 (raw pipe).
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, List, Optional
import numpy as np

from app.data.seed_data import TEAMS, FIXTURES, get_fixtures_by_stage, get_fixtures_by_group
from app.services.prediction import predict_match, build_feature_vector
from app.services.fatigue_engine   import compute_travel_decay
from app.services.chemistry_engine import compute_club_chemistry, compute_xt_compatibility
from app.services.momentum_engine  import compute_clutch_rating, get_momentum_profile
from app.services.tactical_engine  import compute_tactical_neutralisation
from app.services.climate_engine   import compute_climate_delta, compute_schedule_hardship
from app.services.referee_engine   import compute_referee_impact
from app.services.schedule_engine  import compute_schedule_delta

router = APIRouter()

# Mock bookmaker odds — replace with live odds feed integration
MOCK_MARKET_ODDS: Dict[str, Dict] = {
    "BRA": {"home_win": 0.420, "draw": 0.238, "away_win": 0.342},
    "FRA": {"home_win": 0.402, "draw": 0.241, "away_win": 0.357},
    "ENG": {"home_win": 0.312, "draw": 0.261, "away_win": 0.427},
    "ARG": {"home_win": 0.448, "draw": 0.225, "away_win": 0.327},
    "ESP": {"home_win": 0.381, "draw": 0.244, "away_win": 0.375},
}

TEAM_MAP = {t["id"]: t for t in TEAMS}


class DeltaRequest(BaseModel):
    home_id: str
    away_id: str
    ko_round: Optional[str] = "Quarter-finals"
    match_number: int = 5
    rest_hours_a: float = 120.0
    rest_hours_b: float = 120.0
    market_odds: Optional[Dict] = None


@router.post("/delta")
def compute_delta(req: DeltaRequest):
    """
    Core delta computation:
    FieldIQ simulated probability - bookmaker implied probability.
    Returns all three output tiers in one response.
    """
    team_a = TEAM_MAP.get(req.home_id)
    team_b = TEAM_MAP.get(req.away_id)

    if not team_a or not team_b:
        return {"error": f"Team not found: {req.home_id} or {req.away_id}"}

    # ── FieldIQ probabilities ──────────────────────────────────────────────
    probs = predict_match(
        team_a, team_b,
        match_number=req.match_number,
        ko_round=req.ko_round,
        rest_hours_a=req.rest_hours_a,
        rest_hours_b=req.rest_hours_b,
    )
    p_home, p_draw, p_away = float(probs[0]), float(probs[1]), float(probs[2])

    # ── Market odds ────────────────────────────────────────────────────────
    market = req.market_odds or MOCK_MARKET_ODDS.get(req.home_id, {
        "home_win": 0.40, "draw": 0.24, "away_win": 0.36
    })
    m_home = market.get("home_win", 0.40)
    m_draw = market.get("draw", 0.24)
    m_away = market.get("away_win", 0.36)

    # ── Delta computation ──────────────────────────────────────────────────
    delta_home = round(p_home - m_home, 4)
    vig        = 0.048
    edge_score = round(delta_home - (vig / 2 if delta_home > 0 else -vig / 2), 4)
    kelly_full = round(edge_score / (1 - m_home), 4) if edge_score > 0 else 0.0
    kelly_q    = round(kelly_full * 0.25, 4)

    # ── V3 layer breakdown ─────────────────────────────────────────────────
    fa = compute_travel_decay(req.home_id, req.match_number, req.ko_round, req.rest_hours_a)
    fb = compute_travel_decay(req.away_id, req.match_number, req.ko_round, req.rest_hours_b)
    fatigue_delta = round(fb["cumulative_fatigue"] - fa["cumulative_fatigue"], 4)

    tactical = compute_tactical_neutralisation(team_a, team_b)
    tactical_delta = round(tactical["tactical_neutralisation_score"] * 0.08, 4)

    pa = get_momentum_profile(req.home_id)
    pb = get_momentum_profile(req.away_id)
    momentum_delta = round((pa["clutch_rating"] if "clutch_rating" in pa
                            else pa["comeback_rate"]) -
                           (pb["clutch_rating"] if "clutch_rating" in pb
                            else pb["comeback_rate"]), 4) * 0.03

    chemistry_delta = round(fatigue_delta * 0.15, 4)  # proxy without full squad data

    layer_contributions = {
        "FATIGUE_TRAVEL":   round(fatigue_delta * 0.30, 4),
        "CLUB_CHEMISTRY":   round(chemistry_delta, 4),
        "MOMENTUM_CLUTCH":  round(float(momentum_delta), 4),
        "TACTICAL_MATCHUP": round(tactical_delta, 4),
    }
    primary_driver = max(layer_contributions, key=lambda k: abs(layer_contributions[k]))

    # Confidence: wider early, narrower late-tournament
    base_conf = 0.55 + (req.match_number - 1) * 0.03
    model_confidence = round(min(0.88, base_conf), 3)
    ci_half = round(0.04 * (1 - model_confidence * 0.8), 4)

    # ── Time sensitivity ───────────────────────────────────────────────────
    if req.rest_hours_a < 4:    time_sensitivity = "minutes"
    elif req.rest_hours_a < 24: time_sensitivity = "hours"
    elif req.ko_round in ("Round of 32", "Round of 16"): time_sensitivity = "days"
    else:                        time_sensitivity = "pre_tournament"

    # ── Variance / simulation distribution (Monte Carlo proxy) ────────────
    sigma = 0.08
    bins = []
    for i in range(21):
        x = i / 20
        h = np.exp(-0.5 * ((x - p_home) / sigma) ** 2)
        bins.append({"x": round(x, 2), "h": round(float(h), 4)})

    return {
        "version": "3.0",
        "match": {
            "home_id":  req.home_id,
            "away_id":  req.away_id,
            "home_name": team_a["name"],
            "away_name": team_b["name"],
            "home_flag": team_a["flag"],
            "away_flag": team_b["flag"],
            "ko_round":  req.ko_round,
        },

        # ── Tier 1: Sportsbook ─────────────────────────────────────────────
        "probabilities": {
            "model_prob_home":      round(p_home, 4),
            "model_prob_draw":      round(p_draw, 4),
            "model_prob_away":      round(p_away, 4),
            "market_implied_home":  round(m_home, 4),
            "market_implied_draw":  round(m_draw, 4),
            "market_implied_away":  round(m_away, 4),
            "prob_discrepancy_home": delta_home,
            "confidence_interval":  [
                round(max(0, p_home - ci_half), 4),
                round(min(1, p_home + ci_half), 4),
            ],
            "model_confidence":     model_confidence,
            "v3_layer_contribution": layer_contributions,
        },

        # ── Tier 2: Sharp syndicate ────────────────────────────────────────
        "edge": {
            "edge_score_home":       edge_score,
            "kelly_fraction_full":   kelly_full,
            "suggested_fraction_quarter": kelly_q,
            "primary_driver":        primary_driver,
            "time_sensitivity":      time_sensitivity,
            "model_confidence":      model_confidence,
        },

        # ── Tier 3: End user ───────────────────────────────────────────────
        "intelligence": {
            "value_label": (
                "STRONG_VALUE"   if abs(edge_score) > 0.06 else
                "MILD_VALUE"     if abs(edge_score) > 0.02 else
                "FAIR_PRICE"     if abs(edge_score) > -0.01 else
                "OVERPRICED"
            ),
            "confidence_display": min(5, max(1, round(model_confidence * 5))),
            "narrative_flags": [
                f"Travel decay: {team_a['name']} fatigue {fa['cumulative_fatigue']:.3f} vs {team_b['name']} {fb['cumulative_fatigue']:.3f}",
                f"Tactical: {tactical['style_a']} vs {tactical['style_b']} — score {tactical['tactical_neutralisation_score']:.3f}",
                f"Primary edge driver: {primary_driver.replace('_', ' ').title()}",
            ],
        },

        # ── Decomposition data (Layer 2) ───────────────────────────────────
        "decomposition": {
            "waterfall": [
                {"key": k, "value": v, "pct_of_total": round(v / max(abs(delta_home), 0.001) * 100, 1)}
                for k, v in layer_contributions.items()
            ],
            "sim_distribution": bins,
            "tactical_detail":  tactical,
            "fatigue_home":     fa,
            "fatigue_away":     fb,
        },
    }


@router.get("/fixtures")
def command_center_fixtures(stage: str = None, group: str = None):
    """Return all 104 WC 2026 fixtures. Filter by ?stage= or ?group="""
    if group:
        fixtures = get_fixtures_by_group(group.upper())
    elif stage:
        fixtures = get_fixtures_by_stage(stage)
    else:
        fixtures = FIXTURES
    return {
        "fixtures": fixtures,
        "count": len(fixtures),
        "stages": {
            "Group Stage": 72, "Round of 32": 16, "Round of 16": 8,
            "Quarter-finals": 4, "Semi-finals": 2, "Third place": 1, "Final": 1,
        }
    }

# ── Layer 5/6/7 engines ───────────────────────────────────────────────────


class DeepDeltaRequest(BaseModel):
    home_id:            str
    away_id:            str
    group:              str
    matchday:           int = 1
    ko_round:           Optional[str] = None
    match_number:       int = 3
    rest_hours_a:       float = 120.0
    rest_hours_b:       float = 120.0
    fixture_id:         Optional[str] = None
    ref_name:           Optional[str] = None
    ref_confederation:  Optional[str] = None
    market_odds:        Optional[Dict] = None


@router.post("/deep-delta")
def compute_deep_delta(req: DeepDeltaRequest):
    """
    Full FieldIQ intelligence stack — all 7 layers combined.
    Layers 1-4: existing (fatigue, chemistry, momentum, tactical)
    Layer 5: climate asymmetry
    Layer 6: referee variance
    Layer 7: schedule hardship

    Returns everything needed for the Discord intelligence post.
    """
    team_a = TEAM_MAP.get(req.home_id)
    team_b = TEAM_MAP.get(req.away_id)
    if not team_a or not team_b:
        return {"error": f"Unknown team: {req.home_id} or {req.away_id}"}

    # ── Existing layers 1-4 ───────────────────────────────────────────────
    probs = predict_match(
        team_a, team_b,
        match_number=req.match_number,
        ko_round=req.ko_round,
        rest_hours_a=req.rest_hours_a,
        rest_hours_b=req.rest_hours_b,
    )
    p_home, p_draw, p_away = float(probs[0]), float(probs[1]), float(probs[2])

    # Market
    market = req.market_odds or MOCK_MARKET_ODDS.get(req.home_id, {
        "home_win": 0.40, "draw": 0.24, "away_win": 0.36
    })
    m_home = market.get("home_win", 0.40)
    m_draw = market.get("draw", 0.24)
    m_away = market.get("away_win", 0.36)

    delta_home  = round(p_home - m_home, 4)
    vig         = 0.048
    edge_score  = round(delta_home - (vig/2 if delta_home > 0 else -vig/2), 4)
    kelly_full  = round(edge_score / (1 - m_home), 4) if edge_score > 0 else 0.0
    kelly_q     = round(kelly_full * 0.25, 4)

    fa = compute_travel_decay(req.home_id, req.match_number, req.ko_round, req.rest_hours_a)
    fb = compute_travel_decay(req.away_id, req.match_number, req.ko_round, req.rest_hours_b)

    tactical    = compute_tactical_neutralisation(team_a, team_b)
    pa          = get_momentum_profile(req.home_id)
    pb          = get_momentum_profile(req.away_id)

    # ── Layer 5: Climate ──────────────────────────────────────────────────
    climate = compute_climate_delta(
        req.home_id, req.away_id,
        venue="new_york",  # fallback — overridden by fixture_id if provided
        fixture_id=req.fixture_id,
        ko_round=req.ko_round,
    )

    # ── Layer 6: Referee ──────────────────────────────────────────────────
    referee = compute_referee_impact(
        req.home_id, req.away_id,
        home_pdv=team_a.get("pdv", 1.0),
        away_pdv=team_b.get("pdv", 1.0),
        home_srr=team_a.get("srr", 60),
        away_srr=team_b.get("srr", 60),
        ref_name=req.ref_name,
        ref_confederation=req.ref_confederation,
        ko_round=req.ko_round,
    )

    # ── Layer 7: Schedule hardship ────────────────────────────────────────
    schedule = compute_schedule_delta(
        req.home_id, req.away_id,
        group=req.group,
        matchday=req.matchday,
    )

    # ── Composite adjusted probabilities ─────────────────────────────────
    # Climate and schedule deltas nudge the base probabilities
    climate_adj  = climate["climate_delta"] * 0.30
    schedule_adj = schedule["schedule_delta"] * 0.20
    ref_adj      = referee["prob_shift"] * (1 if referee["disciplined_team_edge"] == "home" else -1)

    p_home_adj = max(0.05, min(0.90, p_home + climate_adj + schedule_adj + ref_adj))
    p_away_adj = max(0.05, min(0.90, p_away - climate_adj - schedule_adj))
    p_draw_adj = max(0.05, 1.0 - p_home_adj - p_away_adj)
    total_adj  = p_home_adj + p_draw_adj + p_away_adj
    p_home_adj /= total_adj; p_draw_adj /= total_adj; p_away_adj /= total_adj

    # Adjusted edge
    adj_delta       = round(p_home_adj - m_home, 4)
    adj_edge_score  = round(adj_delta - (vig/2 if adj_delta > 0 else -vig/2), 4)
    adj_kelly       = round(adj_edge_score / (1 - m_home), 4) if adj_edge_score > 0 else 0.0

    # ── Value label ───────────────────────────────────────────────────────
    def value_label(edge):
        if abs(edge) > 0.06: return "STRONG_VALUE"
        if abs(edge) > 0.02: return "MILD_VALUE"
        if abs(edge) > -0.01: return "FAIR_PRICE"
        return "OVERPRICED"

    return {
        "version":      "7.0",
        "match": {
            "home_id":   req.home_id, "away_id":  req.away_id,
            "home_name": team_a["name"], "away_name": team_b["name"],
            "home_flag": team_a["flag"], "away_flag": team_b["flag"],
            "group": req.group, "matchday": req.matchday,
        },

        # ── Base probabilities (MLP layers 1-4) ────────────────────────
        "base": {
            "p_home": round(p_home, 4), "p_draw": round(p_draw, 4), "p_away": round(p_away, 4),
            "market_home": m_home, "market_draw": m_draw, "market_away": m_away,
            "delta": delta_home, "edge_score": edge_score,
            "kelly_quarter": kelly_q,
            "value_label": value_label(edge_score),
        },

        # ── Adjusted probabilities (all 7 layers) ─────────────────────
        "adjusted": {
            "p_home": round(p_home_adj, 4),
            "p_draw": round(p_draw_adj, 4),
            "p_away": round(p_away_adj, 4),
            "delta": adj_delta,
            "edge_score": adj_edge_score,
            "kelly_quarter": round(adj_kelly * 0.25, 4),
            "value_label": value_label(adj_edge_score),
            "climate_contribution":  round(climate_adj, 4),
            "schedule_contribution": round(schedule_adj, 4),
            "referee_contribution":  round(ref_adj, 4),
        },

        # ── Layer 5: Climate ───────────────────────────────────────────
        "climate": {
            "venue":            climate["venue"],
            "temp_c":           climate["temp_c"],
            "humidity_pct":     climate["humidity_pct"],
            "altitude_m":       climate["altitude_m"],
            "indoor_ac":        climate["indoor_ac"],
            "climate_delta":    climate["climate_delta"],
            "heat_adapt_gap":   climate["heat_adapt_gap"],
            "classification":   climate["venue_classification"],
            "home_penalty":     climate["home_climate_penalty"],
            "away_penalty":     climate["away_climate_penalty"],
            "narrative":        climate["narrative"],
        },

        # ── Layer 6: Referee ───────────────────────────────────────────
        "referee": {
            "confederation":        referee["referee_confederation"],
            "cards_multiplier":     referee["cards_multiplier"],
            "penalty_multiplier":   referee["penalty_multiplier"],
            "expected_yellows":     referee["expected_yellows"],
            "penalty_probability":  referee["penalty_probability"],
            "both_teams_carded":    referee["both_teams_carded_prob"],
            "home_suspension_risk": referee["home_suspension_prob"],
            "away_suspension_risk": referee["away_suspension_prob"],
            "penalty_market_edge":  referee["penalty_market_edge"],
            "cards_market_edge":    referee["cards_market_edge"],
            "narrative":            referee["narrative"],
        },

        # ── Layer 7: Schedule hardship ─────────────────────────────────
        "schedule": {
            "home_hardship":      schedule["home_hardship"],
            "away_hardship":      schedule["away_hardship"],
            "schedule_delta":     schedule["schedule_delta"],
            "matchday_delta":     schedule["matchday_delta"],
            "signal":             schedule["signal_strength"],
            "beneficiary":        schedule["beneficiary"],
            "home_tz_shift":      schedule["home_tz_shift"],
            "away_tz_shift":      schedule["away_tz_shift"],
            "home_travel_km":     schedule["home_travel_km"],
            "away_travel_km":     schedule["away_travel_km"],
            "home_class":         schedule["home_hardship_class"],
            "away_class":         schedule["away_hardship_class"],
        },

        # ── Fatigue layer (existing) ───────────────────────────────────
        "fatigue": {
            "home_cumulative": fa["cumulative_fatigue"],
            "away_cumulative": fb["cumulative_fatigue"],
            "home_tz_shift":   fa["tz_shift_hours"],
            "away_tz_shift":   fb["tz_shift_hours"],
        },

        # ── Tactical layer (existing) ──────────────────────────────────
        "tactical": {
            "style_home":       tactical.get("style_a"),
            "style_away":       tactical.get("style_b"),
            "neutralisation":   tactical.get("tactical_neutralisation_score"),
            "high_line_risk":   tactical.get("high_line_risk", False),
        },
    }


@router.get("/schedule-hardship/{group}")
def group_schedule_hardship(group: str):
    """Return schedule hardship scores for all teams in a group."""
    from app.data.seed_data import TEAMS
    group_teams = [t for t in TEAMS if t.get("group", "").upper() == group.upper()]
    results = []
    for t in group_teams:
        h = compute_schedule_hardship(t["id"], group.upper())
        results.append({
            "team": t["name"], "flag": t["flag"],
            "hardship_score": h["schedule_hardship"],
            "hardship_class": h["hardship_class"],
            "tz_shift_hrs":   h["initial_tz_shift_hrs"],
            "travel_km":      h["total_travel_km"],
            "avg_temp_c":     h["avg_temp_c"],
            "temp_range_c":   h["temp_range_c"],
            "md3_penalty":    h["md3_penalty"],
        })
    results.sort(key=lambda x: -x["hardship_score"])
    return {"group": group.upper(), "teams": results}
