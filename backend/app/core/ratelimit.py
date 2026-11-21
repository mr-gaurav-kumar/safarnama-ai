"""Fixed-window rate limiting on top of the cache (§4.13).

    ok, retry_after = check("chat", user_id, limit=10, window_seconds=60)

A fixed window keyed by what + who + which window. Simple and cheap: at most
2x the limit can slip through across a window boundary, which is fine for
protecting an LLM bill from a stuck key or a spammy client. Phase 7 puts the
same function behind every endpoint.
"""
from __future__ import annotations

import time

from app.core.cache import get_cache


def check(scope: str, who: str, *, limit: int, window_seconds: int) -> tuple[bool, int]:
    """(allowed, seconds until the window resets)."""
    now = int(time.time())
    window = now // window_seconds
    count = get_cache().incr(f"rl:{scope}:{who}:{window}", window_seconds + 5)
    retry_after = (window + 1) * window_seconds - now
    return count <= limit, max(retry_after, 1)
