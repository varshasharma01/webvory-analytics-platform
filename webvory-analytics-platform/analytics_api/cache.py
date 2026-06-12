"""
Redis cache helper for Webvory Analytics API.

Provides a simple cached_query() wrapper:
- Check Redis first
- On miss, run the DB function, store result, return it
"""

import os
import json
import redis

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
DEFAULT_TTL = int(os.getenv("CACHE_TTL_SECONDS", "120"))  # 2 minutes

try:
    redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    redis_client.ping()
    REDIS_AVAILABLE = True
    print("Redis connected.")
except Exception as e:
    print(f"Redis not available ({e}). Running without cache.")
    redis_client = None
    REDIS_AVAILABLE = False


def cached_query(cache_key: str, fetch_func, ttl: int = DEFAULT_TTL):
    """
    Returns cached result if present, otherwise calls fetch_func(),
    caches it, and returns it.

    fetch_func: a zero-argument function that returns a JSON-serializable dict/list
    """
    if REDIS_AVAILABLE:
        cached = redis_client.get(cache_key)
        if cached is not None:
            result = json.loads(cached)
            result["_cache"] = "hit"
            return result

    # Cache miss (or Redis down) -> compute fresh
    result = fetch_func()

    if REDIS_AVAILABLE:
        redis_client.setex(cache_key, ttl, json.dumps(result, default=str))

    result["_cache"] = "miss"
    return result