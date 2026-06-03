"""API key authentication middleware."""

from __future__ import annotations

import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.config import settings

logger = logging.getLogger(__name__)

PUBLIC_PATHS = {"/", "/health", "/docs", "/openapi.json", "/redoc"}


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Validate X-API-Key on /v1/* when ENFORCE_API_KEY is enabled."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        if path in PUBLIC_PATHS or path.startswith(("/docs", "/openapi", "/redoc")):
            return await call_next(request)

        if not path.startswith("/v1/"):
            return await call_next(request)

        if not settings.ENFORCE_API_KEY:
            return await call_next(request)

        api_key = request.headers.get("X-API-Key", "")
        if api_key not in settings.valid_api_keys:
            logger.warning("Rejected request — invalid API key on %s", path)
            return JSONResponse(
                status_code=401,
                content={
                    "error": "Invalid or missing API key",
                    "code": "UNAUTHORIZED",
                },
            )

        request.state.api_key = api_key
        return await call_next(request)
