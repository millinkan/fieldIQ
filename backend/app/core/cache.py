"""Redis-backed response cache with in-memory fallback."""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

_redis = None
_memory: dict[str, tuple[Any, float]] = {}
_MEMORY_TTL = 300.0


def _get_redis():
    global _redis
    if _redis is not None:
        return _redis
    try:
        import redis

        client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        client.ping()
        _redis = client
        logger.info("Redis cache connected")
    except Exception as exc:
        logger.warning("Redis unavailable (%s) — using in-memory cache", exc)
        _redis = False
    return _redis


def _cache_key(prefix: str, payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str)
    digest = hashlib.sha256(raw.encode()).hexdigest()[:16]
    return f"fieldiq:{prefix}:{digest}"


def cache_get(prefix: str, payload: dict) -> Optional[Any]:
    key = _cache_key(prefix, payload)
    client = _get_redis()
    if client:
        try:
            val = client.get(key)
            return json.loads(val) if val else None
        except Exception:
            pass
    entry = _memory.get(key)
    if not entry:
        return None
    import time
    if time.time() - entry[1] > _MEMORY_TTL:
        _memory.pop(key, None)
        return None
    return entry[0]


def cache_set(prefix: str, payload: dict, value: Any, ttl: int = 3600) -> None:
    key = _cache_key(prefix, payload)
    serialized = json.dumps(value, default=str)
    client = _get_redis()
    if client:
        try:
            client.setex(key, ttl, serialized)
            return
        except Exception:
            pass
    import time
    _memory[key] = (value, time.time())


def cache_health() -> dict:
    client = _get_redis()
    if not client:
        return {"status": "fallback", "backend": "memory", "keys": len(_memory)}
    try:
        client.ping()
        return {"status": "ok", "backend": "redis"}
    except Exception as exc:
        return {"status": "error", "backend": "redis", "detail": str(exc)}
