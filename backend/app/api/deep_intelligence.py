"""
Deep Intelligence API — v4 additions
======================================
Three new analytical layers that go beyond probability numbers:

  POST /v1/deep/pathways        — Pathways & Ranges Array (named scenario clusters)
  POST /v1/deep/sensitivity     — Sensitivity Index / What-If shock matrix
  POST /v1/deep/asymmetry       — Structural Asymmetry Rating
  POST /v1/deep/full            — All three in one response (the flagship enterprise call)
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, List, Optional
import numpy as np

from app.data.seed_data import TEAMS
from app.core.exceptions import NotFoundError
from app.services.prediction import predict_match
from app.services.pathways_engine   import compute_pathway_clusters
from app.services.sensitivity_engine import compute_sensitivity_index
from app.services.asymmetry_engine   import compute_structural_asymmetry

router = APIRouter()
TEAM_MAP = {t["id"]: t for t in TEAMS}


class DeepRequest(BaseModel):
    home_id:      str
    away_id:      str
    ko_round:     Optional[str]  = "Quarter-finals"
    match_number: int            = 5
    rest_hours_a: float          = 120.0
    rest_hours_b: float          = 120.0
    n_sims:       int            = 10_000
    market_odds:  Optional[Dict] = None


def _get_teams(req: DeepRequest):
    team_a = TEAM_MAP.get(req.home_id)
    team_b = TEAM_MAP.get(req.away_id)
    if not team_a:
        raise NotFoundError("Team", req.home_id)
    if not team_b:
        raise NotFoundError("Team", req.away_id)
    return team_a, team_b


def _base_probs(team_a, team_b, req: DeepRequest) -> np.ndarray:
    return predict_match(
        team_a, team_b,
        match_number=req.match_number,
        ko_round=req.ko_round,
        rest_hours_a=req.rest_hours_a,
        rest_hours_b=req.rest_hours_b,
    )


@router.post("/pathways")
def pathways(req: DeepRequest):
    """
    Map the simulation distribution into named tactical scenario clusters.
    Returns Pathways & Ranges Array — the 'how is the 60% constructed?' answer.
    """
    team_a, team_b = _get_teams(req)
    probs = _base_probs(team_a, team_b, req)
    clusters = compute_pathway_clusters(
        team_a, team_b, probs,
        match_number=req.match_number,
        ko_round=req.ko_round,
        rest_hours_a=req.rest_hours_a,
        rest_hours_b=req.rest_hours_b,
        n_sims=min(req.n_sims, 10_000),
    )
    return {
        "match":    {"home": team_a["name"], "away": team_b["name"], "flag_h": team_a["flag"], "flag_a": team_b["flag"]},
        "baseline": {"p_win": round(float(probs[0]),4), "p_draw": round(float(probs[1]),4), "p_loss": round(float(probs[2]),4)},
        **clusters,
    }


@router.post("/sensitivity")
def sensitivity(req: DeepRequest):
    """
    What-If shock matrix: how does the match equity warp under event shocks?
    Returns engine vs market asymmetry for each shock — the live in-play pricing gaps.
    """
    team_a, team_b = _get_teams(req)
    probs = _base_probs(team_a, team_b, req)
    index = compute_sensitivity_index(
        team_a, team_b, probs,
        match_number=req.match_number,
        ko_round=req.ko_round,
        rest_hours_a=req.rest_hours_a,
        rest_hours_b=req.rest_hours_b,
    )
    return {
        "match": {"home": team_a["name"], "away": team_b["name"], "flag_h": team_a["flag"], "flag_a": team_b["flag"]},
        **index,
    }


@router.post("/asymmetry")
def asymmetry(req: DeepRequest):
    """
    Structural Asymmetry Rating: exposes the mechanism of mispricing,
    not the size of the probability gap.
    This is the enterprise-grade output that replaces "win percentages."
    """
    team_a, team_b = _get_teams(req)
    probs = _base_probs(team_a, team_b, req)
    rating = compute_structural_asymmetry(
        team_a, team_b, probs,
        match_number=req.match_number,
        ko_round=req.ko_round,
        rest_hours_a=req.rest_hours_a,
        rest_hours_b=req.rest_hours_b,
    )
    return {
        "match": {"home": team_a["name"], "away": team_b["name"], "flag_h": team_a["flag"], "flag_a": team_b["flag"]},
        **rating,
    }


@router.post("/full")
def deep_full(req: DeepRequest):
    """
    The flagship enterprise call.
    All three deep intelligence layers in one response:
      - Pathways & Ranges Array
      - Sensitivity Index (What-If shock matrix)
      - Structural Asymmetry Rating
    This is what separates FieldIQ from every data pipe in the market.
    """
    team_a, team_b = _get_teams(req)
    probs = _base_probs(team_a, team_b, req)
    p_win, p_draw, p_loss = float(probs[0]), float(probs[1]), float(probs[2])

    clusters   = compute_pathway_clusters(team_a, team_b, probs,
                    match_number=req.match_number, ko_round=req.ko_round,
                    rest_hours_a=req.rest_hours_a, rest_hours_b=req.rest_hours_b,
                    n_sims=min(req.n_sims, 10_000))

    sensitivity = compute_sensitivity_index(team_a, team_b, probs,
                    match_number=req.match_number, ko_round=req.ko_round,
                    rest_hours_a=req.rest_hours_a, rest_hours_b=req.rest_hours_b)

    rating     = compute_structural_asymmetry(team_a, team_b, probs,
                    match_number=req.match_number, ko_round=req.ko_round,
                    rest_hours_a=req.rest_hours_a, rest_hours_b=req.rest_hours_b)

    return {
        "version": "4.0",
        "match": {
            "home":    team_a["name"],
            "away":    team_b["name"],
            "flag_h":  team_a["flag"],
            "flag_a":  team_b["flag"],
            "ko_round": req.ko_round,
        },
        "baseline_probability": {
            "p_win":  round(p_win,  4),
            "p_draw": round(p_draw, 4),
            "p_loss": round(p_loss, 4),
            "note":   "A flat probability is only the starting point. "
                      "The three layers below explain what is inside it.",
        },
        "pathways":    clusters,
        "sensitivity": sensitivity,
        "asymmetry":   rating,
        "executive_summary": _executive_summary(
            team_a, team_b, clusters, sensitivity, rating, p_win
        ),
    }


def _executive_summary(team_a, team_b, clusters, sensitivity, rating, p_win):
    name_a = team_a.get("name", "Team A")
    name_b = team_b.get("name", "Team B")
    dominant = clusters["clusters"][0] if clusters.get("clusters") else {}
    biggest_shock = sensitivity["shocks"][0] if sensitivity.get("shocks") else {}
    severity = rating.get("severity_label", "NEUTRAL")

    return {
        "one_line": (
            f"{severity} structural asymmetry detected. "
            f"Dominant pathway: {dominant.get('label','—')} "
            f"({dominant.get('pct_of_runs',0):.0f}% of runs, "
            f"modal score {dominant.get('modal_score','—')}). "
            f"Biggest in-play mispricing: {biggest_shock.get('label','—')} "
            f"(asymmetry {biggest_shock.get('asymmetry',0)*100:+.1f}pp vs market)."
        ),
        "for_trading_desk": rating.get("commercial_implication", ""),
        "for_syndicate": (
            f"Edge entry window: before '{biggest_shock.get('event','—')}' line correction. "
            f"Structural asymmetry rating: {rating.get('overall_asymmetry_rating',0):+.4f}. "
            f"Primary anomaly: {rating.get('primary_anomaly',{}).get('id','—') if rating.get('primary_anomaly') else '—'}."
        ),
        "for_fantasy": (
            f"{name_a if p_win > 0.45 else name_b} has structural advantages "
            f"the public odds don't reflect. "
            f"Dominant match pattern: {dominant.get('description','—')}."
        ),
    }
