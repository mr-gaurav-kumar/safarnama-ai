"""Instant place suggestions while typing: "Naini" -> Nainital, "manli" -> Manali.

Everything here is local (no network), so it can answer on every keystroke.
Order: curated travel destinations first (they have coordinates and are what
people plan trips to), then the built-in list of Indian cities. Typos are
caught with a close-match pass once the query has four letters.
"""
from __future__ import annotations

import difflib
import re
from functools import lru_cache

from app.data import cities as india_cities
from app.data.attractions import ATTRACTIONS
from app.data.destinations import DESTINATIONS


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", "", s.lower()).strip()


@lru_cache(maxsize=1)
def _names() -> list[tuple[str, int, bool]]:
    """(normalised name or alias, index into DESTINATIONS, is_alias)."""
    out = []
    for i, d in enumerate(DESTINATIONS):
        out.append((_norm(d.name), i, False))
        out += [(_norm(a), i, True) for a in d.aliases]
    return out


def _rank(q: str, norm: str) -> int | None:
    if norm.startswith(q):
        return 0
    if any(w.startswith(q) for w in norm.split()):
        return 1
    if q in norm:
        return 2
    return None


def suggest(query: str, limit: int = 8) -> list[dict]:
    q = _norm(query)
    if not q:
        return []
    best: dict[int, int] = {}
    for norm, i, alias in _names():
        r = _rank(q, norm)
        if r is not None:
            r = r * 2 + alias  # the real name beats an alias ("ma": Madurai before Chennai/Madras)
            if r < best.get(i, 99):
                best[i] = r
    if len(q) >= 4 and len(best) < 3:  # a typo: "nanital", "manli", "darjiling"
        index = {n: i for n, i, _ in _names()}
        for match in difflib.get_close_matches(q, list(index), n=4, cutoff=0.72):
            best.setdefault(index[match], 9)

    out: list[dict] = []
    for i in sorted(best, key=lambda i: (best[i], DESTINATIONS[i].name)):
        d = DESTINATIONS[i]
        out.append({"name": d.name, "label": f"{d.name}, {d.state}", "lat": d.lat, "lng": d.lng,
                    "kind": "destination", "state": d.state})
    seen = {o["name"].lower() for o in out}
    if len(out) < limit:
        for c in india_cities.search(query, limit * 2):
            if c["name"].lower() not in seen:
                seen.add(c["name"].lower())
                out.append({"name": c["name"], "label": c["label"], "lat": None, "lng": None,
                            "kind": "city", "state": c["state"]})
    return out[:limit]


def attractions_for(destination: str) -> list[str]:
    """Sights for a destination the traveller typed ("Manali, Himachal" works,
    so do aliases like "Kullu")."""
    hits = suggest(destination.split(",")[0], 1)
    if not hits or hits[0]["kind"] != "destination":
        return []
    return list(ATTRACTIONS.get(hits[0]["name"], ()))
