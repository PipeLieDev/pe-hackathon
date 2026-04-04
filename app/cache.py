"""
Valkey/Redis cache helpers.

Falls back to a no-op if Valkey is unavailable or REDIS_URL is not set,
so the app works fine without Valkey in dev.
"""

import json
import os

from flask import g

_redis = None
_DISABLED = False


def _get_redis():
    global _redis, _DISABLED
    if _DISABLED:
        return None
    if _redis is not None:
        return _redis
    url = os.environ.get("REDIS_URL")
    if not url:
        _DISABLED = True
        return None
    try:
        import redis

        _redis = redis.from_url(url, decode_responses=True)
        _redis.ping()
    except Exception:
        _DISABLED = True
        _redis = None
    return _redis


def cache_get(key):
    r = _get_redis()
    if r is None:
        g.x_cache = "MISS"
        return None
    try:
        value = r.get(key)
        if value is not None:
            g.x_cache = "HIT"
            return json.loads(value)
        g.x_cache = "MISS"
        return None
    except Exception:
        g.x_cache = "MISS"
        return None


def cache_set(key, value, ttl=30):
    r = _get_redis()
    if r is None:
        return
    try:
        r.setex(key, ttl, json.dumps(value))
    except Exception:
        pass


def cache_delete(key):
    r = _get_redis()
    if r is None:
        return
    try:
        r.delete(key)
    except Exception:
        pass


def cache_delete_pattern(pattern):
    r = _get_redis()
    if r is None:
        return
    try:
        keys = r.keys(pattern)
        if keys:
            r.delete(*keys)
    except Exception:
        pass
