from app.data.seed_data import SRR_DATA, FIXTURES, get_fixtures_by_group
from app.data.seed_data import TEAMS, FIXTURES, get_fixtures_by_stage, get_fixtures_by_group
from fastapi import APIRouter, Query
from app.data.seed_data import TEAMS


router = APIRouter()

SCENARIOS = ["striker", "mid", "def", "gk"]
SCENARIO_LABELS = {
    "striker": "Striker lost",
    "mid":     "Playmaker lost",
    "def":     "Centre-back lost",
    "gk":      "Goalkeeper lost",
}

# Position-weighted depth factors per scenario
_SCENARIO_WEIGHTS = {
    "striker": {"xg": 0.35, "srr": 0.25, "form": 0.20, "elo": 0.20},
    "mid":     {"xg": 0.20, "srr": 0.35, "form": 0.25, "elo": 0.20},
    "def":     {"xg": 0.15, "srr": 0.30, "form": 0.20, "elo": 0.35},
    "gk":      {"xg": 0.10, "srr": 0.40, "form": 0.15, "elo": 0.35},
}


def compute_srr(team: dict, scenario: str) -> float:
    """Dynamic SRR from team metadata — scales with bench depth proxies."""
    w = _SCENARIO_WEIGHTS[scenario]
    base_srr = team.get("srr", 60)
    xg_factor = min(100, team.get("xg", 1.5) * 35)
    form_factor = team.get("form", 60)
    elo_factor = min(100, team.get("elo", 1700) / 21)

    score = (
        base_srr * w["srr"] +
        xg_factor * w["xg"] +
        form_factor * w["form"] +
        elo_factor * w["elo"]
    )
    return round(min(99, max(20, score)), 1)


def compute_delta(team: dict, scenario: str) -> float:
    """Estimated performance drop if key player in scenario is lost."""
    srr = compute_srr(team, scenario)
    severity = {"striker": 22, "mid": 14, "def": 10, "gk": 18}[scenario]
    pdv_penalty = team.get("pdv", 1.5) * 2
    return round(-(severity + pdv_penalty) * (1 - srr / 100), 1)


@router.get("/rankings")
def srr_rankings(scenario: str = "striker", limit: int = Query(default=16, le=48)):
    """Return SRR rankings for a given loss scenario across all teams."""
    if scenario not in SCENARIOS:
        return {"error": f"scenario must be one of {SCENARIOS}"}

    ranked = sorted(TEAMS, key=lambda t: compute_srr(t, scenario), reverse=True)[:limit]

    return {
        "scenario": scenario,
        "scenario_label": SCENARIO_LABELS[scenario],
        "rankings": [
            {
                "rank": i + 1,
                "flag": t["flag"],
                "name": t["name"],
                "id": t["id"],
                "srr": compute_srr(t, scenario),
                "delta": compute_delta(t, scenario),
                "resilience": (
                    "HIGH" if compute_srr(t, scenario) > 85
                    else "MED" if compute_srr(t, scenario) > 70
                    else "LOW"
                ),
            }
            for i, t in enumerate(ranked)
        ],
    }


@router.get("/all")
def srr_all():
    """Return full SRR table for all scenarios."""
    teams = []
    for t in TEAMS[:16]:
        teams.append({
            "flag": t["flag"],
            "name": t["name"],
            "srr": {sc: compute_srr(t, sc) for sc in SCENARIOS},
            "delta": {sc: compute_delta(t, sc) for sc in SCENARIOS},
        })
    return {"teams": teams, "scenarios": SCENARIOS}


@router.get("/fixtures")
def command_center_fixtures(stage: str = None, group: str = None):
    """
    Return fixtures for the command center delta grid.
    - No params: returns all 104 fixtures
    - ?stage=Group Stage: returns all 72 group matches
    - ?group=A: returns Group A fixtures only
    """
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
            "Group Stage": 72,
            "Round of 32": 16,
            "Round of 16": 8,
            "Quarter-finals": 4,
            "Semi-finals": 2,
            "Third place": 1,
            "Final": 1,
        }
    }
