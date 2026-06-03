"""
V3 Contextual Intelligence API
================================
Exposes all five analytical layers as independent endpoints.

  GET  /v1/v3/fatigue/{team_id}              — Travel decay + rest (+ circadian overlay)
  POST /v1/v3/chemistry                      — Club chemistry + xT compatibility
  GET  /v1/v3/momentum/{team_id}             — Clutch rating + penalty sub advice
  POST /v1/v3/tactical                       — Full tactical matchup matrix
  GET  /v1/v3/psychological/{team_id}        — Morale + circadian psychological context
  GET  /v1/v3/psychological/player/{player_id} — Player-level psych breakdown
  POST /v1/v3/full-analysis                  — All five layers in one response
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, List, Optional

from app.data.seed_data import get_team_squad
from app.services.fatigue_engine   import compute_travel_decay, compute_fatigue_differential
from app.services.chemistry_engine import compute_club_chemistry, compute_xt_compatibility
from app.services.momentum_engine  import (
    compute_clutch_rating, compute_goal_response_delta, compute_penalty_composite
)
from app.services.tactical_engine  import compute_tactical_neutralisation
from app.services.psychological_engine import (
    compute_player_morale,
    compute_player_circadian,
    compute_team_psychological_profile,
)

router = APIRouter()


# ── Request models ─────────────────────────────────────────────────────────

class ChemistryRequest(BaseModel):
    players: List[Dict]


class TacticalRequest(BaseModel):
    team_a: Dict
    team_b: Dict


class FullAnalysisRequest(BaseModel):
    team_a:        Dict
    team_b:        Dict
    match_number:  int   = 1
    ko_round:      Optional[str] = None
    rest_hours_a:  float = 120.0
    rest_hours_b:  float = 120.0
    players_a:     Optional[List[Dict]] = None
    players_b:     Optional[List[Dict]] = None
    yellows_a:     int   = 0
    yellows_b:     int   = 0
    enable_psychological: bool = True
    hours_to_kickoff: float = 48.0


# ── Layer 1: Fatigue ───────────────────────────────────────────────────────

@router.get("/fatigue/{team_id}")
def team_fatigue(
    team_id:     str,
    match_number: int   = 1,
    ko_round:    Optional[str] = None,
    rest_hours:  float  = 120.0,
    hours_to_kickoff: float = 48.0,
    enable_psychological: bool = True,
):
    """
    Physical fatigue and travel decay for a team before a given match.
    Layer 5 circadian overlay applied on top when enable_psychological=true.
    """
    squad = get_team_squad(team_id)
    result = compute_travel_decay(
        team_id, match_number, ko_round, rest_hours,
        players=squad if enable_psychological else None,
        apply_psychological_circadian=enable_psychological,
        hours_to_kickoff=hours_to_kickoff,
    )
    result["team_id"] = team_id

    # Narrative interpretation
    fatigue = result["cumulative_fatigue"]
    if fatigue < 0.10:
        level = "FRESH"
        narrative = "Minimal fatigue — optimal physical condition"
    elif fatigue < 0.20:
        level = "MODERATE"
        narrative = "Some travel fatigue but within manageable range"
    elif fatigue < 0.35:
        level = "SIGNIFICANT"
        narrative = "Notable fatigue — sprint speed and recovery measurably reduced"
    else:
        level = "SEVERE"
        narrative = "High cumulative fatigue — significant physical disadvantage expected"

    result["fatigue_level"]   = level
    result["narrative"]       = narrative
    result["sprint_reduction"] = round((1.0 - result["sprint_speed_mult"]) * 100, 1)
    result["recovery_reduction"] = round((1.0 - result["defensive_recovery"]) * 100, 1)
    if enable_psychological and result.get("circadian_fatigue_uplift", 0) > 0:
        result["circadian_note"] = (
            f"Circadian overlay +{result['circadian_fatigue_uplift']:.3f} on base "
            f"{result.get('base_cumulative_fatigue', result['cumulative_fatigue']):.3f}"
        )
    return result


@router.get("/fatigue-matchup")
def fatigue_matchup(
    team_a_id:   str,
    team_b_id:   str,
    match_number: int   = 1,
    ko_round:    Optional[str] = None,
    rest_hours_a: float = 120.0,
    rest_hours_b: float = 120.0,
):
    """Compare physical fatigue states of two teams before a match."""
    fa = compute_travel_decay(team_a_id, match_number, ko_round, rest_hours_a)
    fb = compute_travel_decay(team_b_id, match_number, ko_round, rest_hours_b)
    diff = compute_fatigue_differential(team_a_id, team_b_id, match_number, ko_round,
                                        rest_hours_a, rest_hours_b)
    return {
        "team_a_id":  team_a_id,
        "team_b_id":  team_b_id,
        "team_a":     fa,
        "team_b":     fb,
        "differential": round(diff, 4),
        "advantage":  team_a_id if diff > 0.02 else (team_b_id if diff < -0.02 else "NEUTRAL"),
    }


# ── Layer 2: Chemistry ─────────────────────────────────────────────────────

@router.post("/chemistry")
def squad_chemistry(req: ChemistryRequest):
    """
    Club-level chemistry from adjacent positional pairs sharing the same club.
    Also computes xT winger/striker compatibility.
    """
    chemistry = compute_club_chemistry(req.players)
    xt        = compute_xt_compatibility(req.players)
    return {
        "club_chemistry":         chemistry,
        "xt_compatibility":       xt,
        "overall_synergy_score":  round(
            chemistry["synergy_multiplier"] * 0.6 + xt["xt_offensive_compat"] * 0.4, 4
        ),
        "interpretation": {
            "synergy_multiplier": f"+{chemistry['synergy_multiplier']*100:.1f}% pass accuracy and defensive compactness",
            "club_pairs":         f"{chemistry['club_pairs_count']} same-club adjacent pairs detected",
            "dominant_club":      chemistry.get("dominant_club") or "No dominant club",
        },
    }


# ── Layer 3: Momentum ──────────────────────────────────────────────────────

@router.get("/momentum/{team_id}")
def team_momentum(
    team_id:            str,
    yellows_accumulated: int = 0,
):
    """
    Psychological resilience: goal response delta, clutch rating, penalty sub advice.
    """
    clutch = compute_clutch_rating(team_id)
    grd    = compute_goal_response_delta(team_id, yellows_accumulated=yellows_accumulated)
    return {
        "team_id":          team_id,
        "clutch_analysis":  clutch,
        "goal_response":    grd,
        "penalty_advice":   clutch.get("penalty_sub_advice", []),
        "narrative": _momentum_narrative(team_id, clutch["clutch_rating"], grd["response_type"]),
    }


def _momentum_narrative(team_id: str, clutch: float, response_type: str) -> str:
    narratives = {
        ("SURGE",   True):  "Elite pressure performers — historically dangerous when trailing",
        ("SURGE",   False): "Lift their game under pressure — hard to hold a lead against",
        ("STABLE",  True):  "Composed under pressure — maintain structure and build steadily",
        ("NEUTRAL", True):  "Average response to adversity — no clear psychological edge",
        ("COLLAPSE",False): "Historical tendency to lose shape after conceding — exploit early",
    }
    high_clutch = clutch > 0.65
    key = (response_type, high_clutch)
    return narratives.get(key, f"{response_type.title()} response pattern, clutch score {clutch:.2f}")


# ── Layer 5: Psychological Context ────────────────────────────────────────

@router.get("/psychological/{team_id}")
def team_psychological(
    team_id: str,
    match_number: int = 1,
    ko_round: Optional[str] = None,
    rest_hours: float = 120.0,
    hours_to_kickoff: float = 48.0,
):
    """Morale vector (A) and circadian overlay context (B) for a squad."""
    squad = get_team_squad(team_id)
    base_fatigue = compute_travel_decay(
        team_id, match_number, ko_round, rest_hours, apply_psychological_circadian=False
    )
    profile = compute_team_psychological_profile(
        team_id, squad, rest_hours, base_fatigue["cumulative_fatigue"], hours_to_kickoff
    )
    profile["base_fatigue"] = base_fatigue["cumulative_fatigue"]
    profile["squad_size"] = len(squad)
    return profile


@router.get("/psychological/player/{player_id}")
def player_psychological(
    player_id: str,
    rest_hours: float = 72.0,
    base_fatigue: float = 0.15,
    hours_to_kickoff: float = 48.0,
):
    """Player-level morale and circadian signal breakdown."""
    return {
        "player_id": player_id,
        "targeted_morale": compute_player_morale(player_id),
        "circadian": compute_player_circadian(
            player_id, rest_hours, base_fatigue, hours_to_kickoff
        ),
    }


# ── Layer 4: Tactical ──────────────────────────────────────────────────────

@router.post("/tactical")
def tactical_matchup(req: TacticalRequest):
    """
    Full tactical style matchup: press efficacy, defensive line risk, style matrix.
    """
    result = compute_tactical_neutralisation(req.team_a, req.team_b)
    return {
        "team_a_style":             result["style_a"],
        "team_b_style":             result["style_b"],
        "matchup_advantage":        result["style_matchup_advantage"],
        "press_analysis":           result["press_analysis"],
        "defensive_line_analysis":  result["defensive_line_analysis"],
        "tactical_score":           result["tactical_neutralisation_score"],
        "late_game_xg_penalty":     result["late_game_xg_penalty"],
        "flags":                    result["tactical_flags"],
        "advantage_team":           (
            req.team_a.get("name", "A") if result["tactical_neutralisation_score"] > 0.05
            else req.team_b.get("name", "B") if result["tactical_neutralisation_score"] < -0.05
            else "NEUTRAL"
        ),
    }


# ── Full Pre-Match Intelligence Report ────────────────────────────────────

@router.post("/full-analysis")
def full_prematch_analysis(req: FullAnalysisRequest):
    """
    Full v3 pre-match intelligence report combining all five contextual layers.
    """
    squad_a = req.players_a or get_team_squad(req.team_a.get("id", ""))
    squad_b = req.players_b or get_team_squad(req.team_b.get("id", ""))

    # Layer 1: Fatigue (+ Layer 5B circadian overlay when enabled)
    fa = compute_travel_decay(
        req.team_a.get("id", ""), req.match_number, req.ko_round, req.rest_hours_a,
        players=squad_a if req.enable_psychological else None,
        apply_psychological_circadian=req.enable_psychological,
        hours_to_kickoff=req.hours_to_kickoff,
    )
    fb = compute_travel_decay(
        req.team_b.get("id", ""), req.match_number, req.ko_round, req.rest_hours_b,
        players=squad_b if req.enable_psychological else None,
        apply_psychological_circadian=req.enable_psychological,
        hours_to_kickoff=req.hours_to_kickoff,
    )
    f_diff = fb["cumulative_fatigue"] - fa["cumulative_fatigue"]

    # Layer 2: Chemistry
    chem_a = compute_club_chemistry(squad_a)
    chem_b = compute_club_chemistry(squad_b)
    xt_a   = compute_xt_compatibility(squad_a)
    xt_b   = compute_xt_compatibility(squad_b)

    # Layer 5: Psychological (morale adjustments before momentum)
    psych_a = psych_b = None
    focus_a = focus_b = 0.0
    if req.enable_psychological:
        psych_a = compute_team_psychological_profile(
            req.team_a.get("id", ""), squad_a, req.rest_hours_a,
            fa.get("base_cumulative_fatigue", fa["cumulative_fatigue"]),
            req.hours_to_kickoff,
        )
        psych_b = compute_team_psychological_profile(
            req.team_b.get("id", ""), squad_b, req.rest_hours_b,
            fb.get("base_cumulative_fatigue", fb["cumulative_fatigue"]),
            req.hours_to_kickoff,
        )
        focus_a = psych_a["morale"]["squad_focus_penalty"]
        focus_b = psych_b["morale"]["squad_focus_penalty"]

    # Layer 3: Momentum (morale-adjusted)
    clutch_a = compute_clutch_rating(req.team_a.get("id", ""), squad_a, focus_a)
    clutch_b = compute_clutch_rating(req.team_b.get("id", ""), squad_b, focus_b)
    grd_a    = compute_goal_response_delta(req.team_a.get("id",""), yellows_accumulated=req.yellows_a)
    grd_b    = compute_goal_response_delta(req.team_b.get("id",""), yellows_accumulated=req.yellows_b)

    # Layer 4: Tactical
    tactical = compute_tactical_neutralisation(req.team_a, req.team_b)

    # Composite edge score for team_a [−1 to 1]
    edge_score = round(
        f_diff * 0.20 +
        (chem_a["synergy_multiplier"] - chem_b["synergy_multiplier"]) * 0.15 +
        (clutch_a["clutch_rating"] - clutch_b["clutch_rating"]) * 0.25 +
        tactical["tactical_neutralisation_score"] * 0.40,
        4
    )

    return {
        "version":    "3.0",
        "team_a":     req.team_a.get("name", "Team A"),
        "team_b":     req.team_b.get("name", "Team B"),
        "edge_score": edge_score,
        "edge_label": ("TEAM_A" if edge_score > 0.05 else "TEAM_B" if edge_score < -0.05 else "NEUTRAL"),
        "layers": {
            "layer_1_fatigue": {
                "team_a_fatigue":    fa["cumulative_fatigue"],
                "team_b_fatigue":    fb["cumulative_fatigue"],
                "differential":      round(f_diff, 4),
                "team_a_rest_hours": req.rest_hours_a,
                "team_b_rest_hours": req.rest_hours_b,
            },
            "layer_2_chemistry": {
                "team_a_synergy":    chem_a["synergy_multiplier"],
                "team_b_synergy":    chem_b["synergy_multiplier"],
                "team_a_pairs":      chem_a["club_pairs_count"],
                "team_b_pairs":      chem_b["club_pairs_count"],
                "team_a_xt_compat":  xt_a["xt_offensive_compat"],
                "team_b_xt_compat":  xt_b["xt_offensive_compat"],
                "team_a_warnings":   xt_a.get("style_warnings", []),
                "team_b_warnings":   xt_b.get("style_warnings", []),
            },
            "layer_3_momentum": {
                "team_a_clutch":     clutch_a["clutch_rating"],
                "team_b_clutch":     clutch_b["clutch_rating"],
                "team_a_response":   grd_a["response_type"],
                "team_b_response":   grd_b["response_type"],
                "team_a_pen_score":  clutch_a["penalty_composite"],
                "team_b_pen_score":  clutch_b["penalty_composite"],
                "penalty_sub_a":     clutch_a.get("penalty_sub_advice", [])[:2],
                "penalty_sub_b":     clutch_b.get("penalty_sub_advice", [])[:2],
            },
            "layer_4_tactical": {
                "style_a":           tactical["style_a"],
                "style_b":           tactical["style_b"],
                "matchup_advantage": tactical["style_matchup_advantage"],
                "press_analysis":    tactical["press_analysis"],
                "high_line_risk":    tactical["defensive_line_analysis"]["high_line_risk_flag"],
                "tactical_score":    tactical["tactical_neutralisation_score"],
                "flags":             tactical["tactical_flags"],
            },
            "layer_5_psychological": {
                "enabled":           req.enable_psychological,
                "team_a_focus_penalty_pct": round(focus_a * 100, 1),
                "team_b_focus_penalty_pct": round(focus_b * 100, 1),
                "team_a_circadian_uplift": psych_a["circadian_uplift"] if psych_a else 0.0,
                "team_b_circadian_uplift": psych_b["circadian_uplift"] if psych_b else 0.0,
                "team_a_flagged_morale": psych_a["morale"]["flagged_players"] if psych_a else [],
                "team_b_flagged_morale": psych_b["morale"]["flagged_players"] if psych_b else [],
                "team_a_circadian_players": (
                    psych_a["circadian"].get("flagged_players", []) if psych_a else []
                ),
                "team_b_circadian_players": (
                    psych_b["circadian"].get("flagged_players", []) if psych_b else []
                ),
            },
        },
    }
