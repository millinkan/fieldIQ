from fastapi import APIRouter, Query

from app.core.cache import cache_get, cache_set
from app.core.config import settings
from app.data.seed_data import TEAMS, PLAYERS
from app.schemas.simulation import SimulateRequest
from app.services.prediction import SimulationConfig, run_monte_carlo

router = APIRouter()


@router.post("/simulate")
def simulate_tournament(req: SimulateRequest):
    """
    Run full 48-team WC 2026 Monte Carlo simulation with v3 contextual layers.
    Feature weights and layer toggles directly affect inference.
    """
    player_ratings = {p["id"]: p["rating"] for p in PLAYERS}
    n = min(req.n_simulations, settings.MC_SIMULATIONS)

    config = SimulationConfig(weights=req.weights, layers=req.layers)

    cache_payload = req.cache_payload()
    if req.use_cache:
        cached = cache_get("simulate", cache_payload)
        if cached:
            cached["cached"] = True
            return cached

    result = run_monte_carlo(
        teams=TEAMS,
        n_sims=n,
        injuries=req.injuries or {},
        player_ratings=player_ratings,
        config=config,
    )
    result["cached"] = False

    if req.use_cache:
        cache_set("simulate", cache_payload, result, ttl=settings.CACHE_TTL_SIMULATION)

    return result


@router.get("/teams")
def get_teams():
    return {"teams": TEAMS, "count": len(TEAMS)}


@router.get("/champion-odds")
def champion_odds(n: int = Query(default=500, le=2000)):
    """Quick champion probability table with v3 layers active."""
    result = run_monte_carlo(TEAMS, n_sims=n)
    return {
        "champion_probs": result["champion_probs"],
        "top_5": list(result["champion_probs"].items())[:5],
        "version": "3.0",
    }
