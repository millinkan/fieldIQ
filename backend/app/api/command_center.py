"""
Command Center API — Delta Dashboard endpoints.
Powers Layer 1 (delta grid), Layer 2 (decomposition), and Layer 3 (raw pipe).
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, List, Optional
import numpy as np

from app.data.seed_data import TEAMS
from app.core.exceptions import NotFoundError
from app.services.prediction import predict_match
from app.services.fatigue_engine import compute_travel_decay
from app.services.momentum_engine import get_momentum_profile
from app.services.tactical_engine  import compute_tactical_neutralisation

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

    if not team_a:
        raise NotFoundError("Team", req.home_id)
    if not team_b:
        raise NotFoundError("Team", req.away_id)

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
    """
    Return fixtures for the command center delta grid.
    - No params: returns all 104 fixtures
    - ?stage=Group Stage: returns all 72 group matches
    - ?stage=Quarter-finals: returns QF fixtures
    - ?group=A: returns Group A fixtures only
    """
    if group:
        fixtures = get_fixtures_by_group(group.upper())
    elif stage:
        fixtures = get_fixtures_by_stage(stage)
    else:
        fixtures = FIXTURES

    # For group stage matches, only return ones with real team IDs
    # For KO rounds, return slot notation so frontend can show bracket
    return {
        "fixtures": fixtures,
        "count": len(fixtures),
        "stages": {
            "Group Stage": 72,
            "Round of 32": 16,
            "Round of 16": 8,
            "Quarter-finals": 4,
            "Semi-finals": 2,
            "Third place": 1,
            "Final": 1,
        }
    }
