from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
import numpy as np

from app.data.seed_data import PDV_COHORT, PLAYERS

router = APIRouter()


class CascadeRequest(BaseModel):
    player_id: str
    match_number: int = 1
    yellows_in_tournament: int = 0


def compute_pdv(yellow_per90: float, reds_season: int,
                late_foul_rate: float, suspension_cover: float) -> float:
    """PDV = (yellows/90 × 0.5) + (reds × 2.5) + (late_foul × 1.8) − (cover × 0.9)"""
    return round(
        yellow_per90 * 0.5 + reds_season * 2.5 + late_foul_rate * 1.8 - suspension_cover * 0.9,
        2,
    )


@router.get("/scores")
def get_pdv_scores():
    """Return PDV scores for the full WC 2026 cohort."""
    return {"players": PDV_COHORT}


@router.post("/cascade")
def pdv_cascade(req: CascadeRequest):
    """
    Given a player's current tournament status, simulate the
    suspension probability and downstream team performance impact.
    """
    player = next((p for p in PLAYERS if p["id"] == req.player_id), None)
    if not player:
        return {"error": f"Player '{req.player_id}' not found"}

    pdv = compute_pdv(
        player["yellow_per90"], player["reds_season"],
        player["late_foul_rate"], player["suspension_cover"],
    )

    # Suspension probability compounds with KO round depth + yellows accumulated
    base_risk = pdv * 0.12 * req.match_number
    yellow_modifier = req.yellows_in_tournament * 0.18
    suspension_prob = round(min(0.95, base_risk + yellow_modifier), 3)

    # Performance drop if suspended
    perf_drop = round(-pdv * 0.06, 3)

    return {
        "player_id":       req.player_id,
        "player_name":     player["name"],
        "team_id":         player["team_id"],
        "pdv_score":       pdv,
        "match_number":    req.match_number,
        "suspension_prob": suspension_prob,
        "suspension_pct":  round(suspension_prob * 100, 1),
        "perf_drop_if_suspended": perf_drop,
        "perf_drop_pct":   round(perf_drop * 100, 1),
        "risk_level":      "HIGH" if pdv > 2.0 else "MED" if pdv > 1.3 else "LOW",
        "formula": {
            "yellows_per90": player["yellow_per90"],
            "reds_season":   player["reds_season"],
            "late_foul_rate": player["late_foul_rate"],
            "suspension_cover": player["suspension_cover"],
        },
    }


@router.get("/formula")
def pdv_formula():
    return {
        "formula": "PDV = (yellows_per_90 × 0.5) + (red_cards_season × 2.5) + (late_game_foul_rate × 1.8) − (suspension_cover_score × 0.9)",
        "weights": {"yellow_per90": 0.5, "reds_season": 2.5, "late_foul_rate": 1.8, "suspension_cover": -0.9},
        "thresholds": {"HIGH": "> 2.0", "MED": "1.3 – 2.0", "LOW": "< 1.3"},
    }
