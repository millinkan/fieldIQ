"""API key validation and credit deduction."""

from __future__ import annotations

import logging
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.config import settings

logger = logging.getLogger(__name__)

# Credits per endpoint (0 = free)
ENDPOINT_COSTS: dict[str, int] = {
    "/v1/tournament/simulate": 10,
    "/v1/tournament/champion-odds": 5,
    "/v1/squad/synergy": 3,
    "/v1/pdv/cascade": 2,
    "/v1/srr/rankings": 1,
    "/v1/model/rankings": 1,
    "/v1/v3/full-analysis": 5,
    "/v1/v3/psychological": 2,
    "/v1/v3/tactical": 2,
    "/v1/v3/chemistry": 2,
    "/v1/model/train": 0,
    "/v1/command/delta": 3,
    "/v1/command/fixtures": 0,
    "/v1/deep/pathways": 5,
    "/v1/deep/sensitivity": 4,
    "/v1/deep/asymmetry": 4,
    "/v1/deep/full": 12,
}

DEMO_BALANCES: dict[str, dict] = {
    "demo": {"tier": "pro", "total": 25_000, "used": 0},
    "analyst": {"tier": "analyst", "total": 5_000, "used": 0},
    "enterprise": {"tier": "enterprise", "total": -1, "used": 0},
}

SKIP_PREFIXES = ("/health", "/docs", "/openapi", "/redoc", "/")


def _match_cost(path: str) -> int:
    for prefix, cost in ENDPOINT_COSTS.items():
        if path == prefix or path.startswith(prefix + "/"):
            return cost
    return 0


def _get_balance(api_key: str) -> dict:
    if api_key in DEMO_BALANCES:
        return DEMO_BALANCES[api_key]
    return DEMO_BALANCES["demo"]


def _deduct(api_key: str, cost: int) -> bool:
    bal = _get_balance(api_key)
    if bal["total"] == -1:
        return True
    remaining = bal["total"] - bal["used"]
    if remaining < cost:
        return False
    bal["used"] += cost
    return True


class CreditsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        if any(path == p or path.startswith(p) for p in SKIP_PREFIXES if p != "/"):
            if path in ("/", "/health") or path.startswith(("/docs", "/openapi", "/redoc")):
                return await call_next(request)

        if not path.startswith("/v1/"):
            return await call_next(request)

        cost = _match_cost(path)
        api_key = request.headers.get("X-API-Key", settings.DEFAULT_API_KEY)

        if cost > 0 and settings.ENFORCE_CREDITS:
            if not _deduct(api_key, cost):
                bal = _get_balance(api_key)
                remaining = bal["total"] - bal["used"]
                return JSONResponse(
                    status_code=402,
                    content={
                        "error": "Insufficient credits",
                        "code": "INSUFFICIENT_CREDITS",
                        "required": cost,
                        "remaining": remaining,
                    },
                )

        response = await call_next(request)
        if cost > 0:
            response.headers["X-Credits-Cost"] = str(cost)
        return response
