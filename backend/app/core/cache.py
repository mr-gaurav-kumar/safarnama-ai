"""A small JSON cache with expiry -- Redis when it is available, this process's
memory when it is not.

TASK_BACKEND=celery already needs Redis, so the cache uses it there and every
process (API, worker) shares one cache. In inline mode there is one process, so
an in-memory cache is enough and nothing extra has to run.

Values must be JSON-serialisable. A cache failure is never an error: `get`
returns None and `set` does nothing, and the caller does the real lookup.
"""
from __future__ import annotations

import json
import logging
import threading
import time
from typing import Any, Protocol

from app.core.config import settings

logger = logging.getLogger(__name__)

KEY_PREFIX = "tp:cache:"


class Cache(Protocol):
    def get(self, key: str) -> Any | None: ...
    def set(self, key: str, value: Any, ttl_seconds: int) -> None: ...
    def incr(self, key: str, ttl_seconds: int) -> int:
        """Add one and return the new count; the key expires `ttl_seconds`
        after it was first created."""
        ...


class MemoryCache:
    MAX_ENTRIES = 5000

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._data: dict[str, tuple[float, str]] = {}

    def get(self, key: str) -> Any | None:
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                return None
            expires_at, raw = entry
            if expires_at < time.monotonic():
                del self._data[key]
                return None
        return json.loads(raw)

    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        raw = json.dumps(value)
        with self._lock:
            if len(self._data) >= self.MAX_ENTRIES:
                # Drop the entry closest to expiry -- crude, but bounded.
                oldest = min(self._data, key=lambda k: self._data[k][0])
                del self._data[oldest]
            self._data[key] = (time.monotonic() + ttl_seconds, raw)

    def incr(self, key: str, ttl_seconds: int) -> int:
        with self._lock:
            entry = self._data.get(key)
            now = time.monotonic()
            if entry is None or entry[0] < now:
                self._data[key] = (now + ttl_seconds, "1")
                return 1
            expires_at, raw = entry
            count = int(json.loads(raw)) + 1
            self._data[key] = (expires_at, json.dumps(count))
            return count

    def clear(self) -> None:
        with self._lock:
            self._data.clear()


class RedisCache:
    def __init__(self, url: str, client=None) -> None:
        import redis

        self._client = client or redis.Redis.from_url(url, socket_timeout=2)

    def get(self, key: str) -> Any | None:
        try:
            raw = self._client.get(KEY_PREFIX + key)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Cache read failed for %s: %s", key, exc)
            return None
        return None if raw is None else json.loads(raw)

    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        try:
            self._client.set(KEY_PREFIX + key, json.dumps(value), ex=ttl_seconds)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Cache write failed for %s: %s", key, exc)

    def incr(self, key: str, ttl_seconds: int) -> int:
        full = KEY_PREFIX + key
        try:
            pipe = self._client.pipeline()
            pipe.incr(full)
            # NX: set the expiry only when the key is new, so the window is
            # fixed rather than sliding forward with every request.
            pipe.expire(full, ttl_seconds, nx=True)
            count, _ = pipe.execute()
            return int(count)
        except Exception as exc:  # noqa: BLE001
            # Fail open: a Redis hiccup should not lock everyone out.
            logger.warning("Cache incr failed for %s: %s", key, exc)
            return 0


_cache: Cache | None = None
_lock = threading.Lock()


def get_cache() -> Cache:
    global _cache
    if _cache is None:
        with _lock:
            if _cache is None:
                _cache = (
                    RedisCache(settings.REDIS_URL)
                    if settings.TASK_BACKEND == "celery"
                    else MemoryCache()
                )
    return _cache
