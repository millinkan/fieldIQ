"""Per-IP rate limiting with Redis fallback."""

from __future__ import annotations

import logging
import time
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.config import settings

logger = logging.getLogger(__name__)

_memory_buckets: dict[str, list[float]] = defaultdict(list)
_redis = None


def _get_redis():
    global _redis
    if _redis is not None:
        return _redis
    try:
        import redis
        client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        client.ping()
        _redis = client
    except Exception:
        _redis = False
    return _redis


def _client_id(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def _check_rate_limit(client_id: str) -> tuple[bool, int]:
    limit = settings.RATE_LIMIT_PER_MINUTE
    window = 60
    now = time.time()
    key = f"fieldiq:rl:{client_id}"

    client = _get_redis()
    if client:
        try:
            pipe = client.pipeline()
            pipe.zremrangebyscore(key, 0, now - window)
            pipe.zadd(key, {str(now): now})
            pipe.zcard(key)
            pipe.expire(key, window + 1)
            _, _, count, _ = pipe.execute()
            remaining = max(0, limit - int(count))
            return int(count) <= limit, remaining
        except Exception:
            pass

    bucket = _memory_buckets[client_id]
    _memory_buckets[client_id] = [t for t in bucket if now - t < window]
    if len(_memory_buckets[client_id]) >= limit:
        return False, 0
    _memory_buckets[client_id].append(now)
    return True, limit - len(_memory_buckets[client_id])


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not settings.ENFORCE_RATE_LIMIT:
            return await call_next(request)

        path = request.url.path
        if path in ("/", "/health") or path.startswith(("/docs", "/openapi", "/redoc")):
            return await call_next(request)

        client_id = _client_id(request)
        allowed, remaining = _check_rate_limit(client_id)
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "code": "RATE_LIMIT",
                    "retry_after_seconds": 60,
                },
                headers={"Retry-After": "60"},
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
