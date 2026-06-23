"""Redis cache utilities.

When REDIS_URL is empty (or Redis is unreachable), all operations are silent no-ops —
the app works correctly without caching, just slower.
"""

import hashlib
import json
from typing import Any

import redis.asyncio as aioredis

_client: aioredis.Redis | None = None

# TTLs in seconds.
SEARCH_TTL = 300     # 5 min — results change as documents are added / removed
EMB_TTL = 86_400     # 24 h  — query embeddings are deterministic


async def init_redis(url: str) -> None:
    global _client
    if not url:
        return
    _client = aioredis.from_url(url, decode_responses=True)
    await _client.ping()  # raises if Redis is unreachable


async def close_redis() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


async def get_cached(key: str) -> Any | None:
    if _client is None:
        return None
    try:
        raw = await _client.get(key)
        return json.loads(raw) if raw is not None else None
    except Exception:
        return None  # Redis unavailable — treat as cache miss


async def set_cached(key: str, value: Any, ttl: int) -> None:
    if _client is None:
        return
    try:
        await _client.set(key, json.dumps(value), ex=ttl)
    except Exception:
        pass  # Redis unavailable — skip silently


async def invalidate_search_cache() -> int:
    """Delete all search result cache keys. Returns number of keys deleted."""
    if _client is None:
        return 0
    try:
        keys = []
        async for key in _client.scan_iter("search:*", count=200):
            keys.append(key)
        if keys:
            await _client.delete(*keys)
        return len(keys)
    except Exception:
        return 0


def search_key(
    model: str, question: str, doc_ids: list[str] | None, semantic: bool = False
) -> str:
    """Deterministic cache key for a hybrid search call."""
    payload = f"{model}\x00{question}\x00{json.dumps(sorted(doc_ids or []))}\x00{int(semantic)}"
    digest = hashlib.sha256(payload.encode()).hexdigest()[:24]
    return f"search:{digest}"
