from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
import numpy as np

from app.data.seed_data import TEAMS, get_team_squad

router = APIRouter()


class PlayerStatus(BaseModel):
    player_id: str
    status: str  # "ok" | "injured" | "bench"


class SynergyRequest(BaseModel):
    team_id: str
    opponent_id: str
    player_statuses: List[PlayerStatus]


def _opponent_adjustments(opponent_id: Optional[str]) -> dict:
    if not opponent_id:
        return {"xg_delta": 0.0, "xga_delta": 0.0, "press_delta": 0}
    opp = next((t for t in TEAMS if t["id"] == opponent_id), None)
    if not opp:
        return {"xg_delta": 0.0, "xga_delta": 0.0, "press_delta": 0}
    elo_norm = (opp.get("elo", 1500) - 1500) / 500
    return {
        "xg_delta": -round(elo_norm * 0.12, 3),
        "xga_delta": round(opp.get("xg", 1.5) * 0.08, 3),
        "press_delta": -int((10 - opp.get("ppda", 10)) * 2),
    }


def compute_synergy(
    active_players: list,
    injured_players: list,
    opponent_id: Optional[str] = None,
) -> dict:
    if not active_players:
        return {"synergy_score": 0, "xg_projected": 0, "press_intensity": 0, "xga_exposed": 0}

    avg_rating = np.mean([p["rating"] for p in active_players])
    avg_pdv = np.mean([p["pdv"] for p in active_players])
    inj_count = len(injured_players)
    inj_penalty = sum((p["rating"] - 70) * 0.03 for p in injured_players)
    opp = _opponent_adjustments(opponent_id)

    synergy = float(np.clip(avg_rating - inj_penalty * 3 - avg_pdv * 0.8, 40, 99))
    xg = float(np.clip(2.41 - inj_penalty * 0.18 - avg_pdv * 0.05 + opp["xg_delta"], 0.4, 3.5))
    press = max(30, round(68 - inj_count * 5 + opp["press_delta"]))
    xga = float(np.clip(1.12 + inj_penalty * 0.12 + opp["xga_delta"], 0.5, 3.5))

    dims = {
        "attacking_synergy": float(np.clip(82 - inj_count * 4, 10, 99)),
        "defensive_shape": float(np.clip(78 - inj_count * 3, 10, 99)),
        "press_cohesion": float(np.clip(71 - inj_count * 4, 10, 99)),
        "set_piece_threat": float(np.clip(65 - inj_count * 3, 10, 99)),
        "tactical_flexibility": float(np.clip(74 - inj_count * 3, 10, 99)),
        "pdv_adjusted_risk": float(np.clip((1 - avg_pdv / 4) * 100, 10, 99)),
    }

    return {
        "synergy_score": round(synergy, 1),
        "xg_projected": round(xg, 2),
        "press_intensity": press,
        "xga_exposed": round(xga, 2),
        "synergy_dimensions": dims,
        "active_count": len(active_players),
        "injured_count": inj_count,
        "bench_count": 0,
        "opponent_adjustments": opp,
    }


@router.post("/synergy")
def squad_synergy(req: SynergyRequest):
    """Compute roster-adjusted synergy vector for a given lineup."""
    team_players = get_team_squad(req.team_id)
    status_map = {ps.player_id: ps.status for ps in req.player_statuses}

    active = [p for p in team_players if status_map.get(p["id"], "ok") == "ok"]
    injured = [p for p in team_players if status_map.get(p["id"], "ok") == "injured"]
    bench = [p for p in team_players if status_map.get(p["id"], "ok") == "bench"]

    result = compute_synergy(active, injured, req.opponent_id)
    result["bench_count"] = len(bench)
    result["team_id"] = req.team_id
    result["opponent_id"] = req.opponent_id
    result["injured_players"] = [p["name"] for p in injured]

    return result


@router.get("/players/{team_id}")
def get_players(team_id: str):
    players = get_team_squad(team_id)
    return {"team_id": team_id, "players": players, "count": len(players)}
