from fastapi import APIRouter
from datetime import datetime, timezone

router = APIRouter()

# Demo credit balances - replace with real DB in production
DEMO_CREDITS = {
    "analyst":    {"total": 5_000,  "used": 1_247, "tier": "Analyst"},
    "pro":        {"total": 25_000, "used": 6_580, "tier": "Pro"},
    "enterprise": {"total": -1,     "used": 0,      "tier": "Enterprise"},
}


@router.get("/balance")
def credit_balance(tier: str = "pro"):
    """Return current credit pool status."""
    info = DEMO_CREDITS.get(tier.lower(), DEMO_CREDITS["pro"])
    remaining = info["total"] - info["used"] if info["total"] != -1 else -1

    now = datetime.now(timezone.utc)
    reset = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if reset.month == 12:
        reset = reset.replace(year=reset.year + 1, month=1)
    else:
        reset = reset.replace(month=reset.month + 1)

    return {
        "tier":              info["tier"],
        "credits_total":     info["total"],
        "credits_used":      info["used"],
        "credits_remaining": remaining,
        "burst_lane":        "active" if tier.lower() == "enterprise" else "pooled",
        "rollover_banked":   round(info["used"] * 0.05),
        "reset_utc":         reset.isoformat(),
        "pricing": {
            "analyst":    {"monthly_usd": 49,   "credits": 5_000,  "burst": False},
            "pro":        {"monthly_usd": 199,  "credits": 25_000, "burst": True},
            "enterprise": {"monthly_usd": None, "credits": -1,     "burst": True, "sla": True},
        },
    }


@router.get("/endpoints")
def api_endpoints():
    return {
        "endpoints": [
            {"method": "POST", "path": "/v1/tournament/simulate",  "credits_per_call": 10,  "desc": "Full 48-team Monte Carlo simulation"},
            {"method": "POST", "path": "/v1/squad/synergy",        "credits_per_call": 3,   "desc": "Roster-adjusted synergy vector"},
            {"method": "POST", "path": "/v1/pdv/cascade",          "credits_per_call": 2,   "desc": "Suspension cascade simulation"},
            {"method": "GET",  "path": "/v1/srr/rankings",         "credits_per_call": 1,   "desc": "Squad Robustness Rating"},
            {"method": "GET",  "path": "/v1/model/rankings",       "credits_per_call": 1,   "desc": "Champion probability rankings"},
            {"method": "GET",  "path": "/v1/tournament/champion-odds", "credits_per_call": 5, "desc": "Quick champion odds"},
            {"method": "GET",  "path": "/v1/v3/fatigue/{team_id}",     "credits_per_call": 1,  "desc": "Travel decay & fatigue analysis"},
            {"method": "GET",  "path": "/v1/v3/psychological/{team_id}", "credits_per_call": 2, "desc": "Morale + circadian psychological context"},
            {"method": "GET",  "path": "/v1/v3/psychological/player/{id}", "credits_per_call": 1, "desc": "Player psychological breakdown"},
            {"method": "POST", "path": "/v1/v3/full-analysis",        "credits_per_call": 5,  "desc": "Full pre-match intelligence report"},
            {"method": "POST", "path": "/v1/v3/tactical",              "credits_per_call": 2,  "desc": "Tactical style matchup matrix"},
            {"method": "POST", "path": "/v1/model/train",              "credits_per_call": 0,  "desc": "Trigger model retraining pipeline"},
            {"method": "GET",  "path": "/v1/model/data-sources",       "credits_per_call": 0,  "desc": "Live data provider status"},
            {"method": "GET",  "path": "/v1/credits/balance",          "credits_per_call": 0,  "desc": "Credit pool status"},
        ],
        "burst_policy": {
            "match_day_multiplier": 3.0,
            "idle_rollover_rate":   0.05,
            "enterprise_burst_lane": "guaranteed",
        },
    }
