"""GET /geo/search and /geo/reverse -- the destination picker's map search.

Calls go through the backend (not the browser straight to OpenStreetMap) so
Nominatim's rules -- identifying User-Agent, 1 request/second, caching -- are
enforced in one place.
"""
from fastapi import APIRouter, HTTPException, Query

from app.data import cities as india_cities
from app.geo.geocode import GeocoderUnavailable, reverse_place, search_indian_places, search_places
from app.geo.suggest import attractions_for, suggest as suggest_places

router = APIRouter(prefix="/geo", tags=["geo"])

_UNAVAILABLE = HTTPException(503, "Place search is unavailable right now. Try again shortly.")


@router.get("/search")
def search(q: str = Query(min_length=2, max_length=120), limit: int = Query(6, ge=1, le=10)) -> list[dict]:
    try:
        return [p.__dict__ for p in search_places(q, limit)]
    except GeocoderUnavailable:
        raise _UNAVAILABLE from None


@router.get("/reverse")
def reverse(lat: float = Query(ge=-90, le=90), lng: float = Query(ge=-180, le=180)) -> dict | None:
    try:
        place = reverse_place(lat, lng)
    except GeocoderUnavailable:
        raise _UNAVAILABLE from None
    return place.__dict__ if place else None


@router.get("/cities")
def cities(q: str = Query(min_length=1, max_length=80), limit: int = Query(8, ge=1, le=20)) -> list[dict]:
    """Indian city + state suggestions as you type. Instant from the built-in
    list; for a rarer town (3+ letters, few local hits) it also asks the map
    search, India only. A map-search outage just means fewer suggestions."""
    results = india_cities.search(q, limit)
    if len(results) < 3 and len(q.strip()) >= 3:
        try:
            seen = {(r["name"].lower(), r["state"].lower()) for r in results}
            for r in search_indian_places(q, 5):
                if (r["name"].lower(), r["state"].lower()) not in seen:
                    results.append(r)
        except GeocoderUnavailable:
            pass
    return results[:limit]


@router.get("/suggest")
def suggest(q: str = Query(min_length=1, max_length=80), limit: int = Query(8, ge=1, le=15)) -> list[dict]:
    """Instant, offline place suggestions as you type: travel destinations
    first, then Indian cities. Catches typos ("nanital" -> Nainital)."""
    return suggest_places(q, limit)


@router.get("/attractions")
def attractions(destination: str = Query(min_length=2, max_length=200)) -> list[str]:
    """Well-known sights at a destination, for the plan editor's "Where" field."""
    return attractions_for(destination)
