"""Indian cities with their state, for the city pickers on sign-up and profile.

`india_cities.json` is a static list (~1,270 places): the larger cities in
population order, plus the tourist towns travellers actually live near or go
to. Anything not in it falls back to an India-only place search.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

_FILE = Path(__file__).with_name("india_cities.json")


@lru_cache(maxsize=1)
def _cities() -> list[tuple[str, str, str]]:
    rows = json.loads(_FILE.read_text(encoding="utf-8"))
    return [(r["name"], r["state"], _norm(r["name"])) for r in rows]


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", "", s.lower()).strip()


def search(query: str, limit: int = 8) -> list[dict]:
    """Prefix matches first (by city size), then word-prefix, then substring.
    The state is searchable too: 'raj' finds Rajkot and Rajasthan's cities."""
    q = _norm(query)
    if not q:
        return []
    prefix, word, contains, by_state = [], [], [], []
    for i, (name, state, norm) in enumerate(_cities()):
        if norm.startswith(q):
            prefix.append(i)
        elif any(w.startswith(q) for w in norm.split()):
            word.append(i)
        elif q in norm:
            contains.append(i)
        elif len(q) >= 3 and _norm(state).startswith(q):
            by_state.append(i)
    picked = (prefix + word + contains + by_state)[:limit]
    rows = _cities()
    return [{"name": rows[i][0], "state": rows[i][1], "label": f"{rows[i][0]}, {rows[i][1]}"} for i in picked]
