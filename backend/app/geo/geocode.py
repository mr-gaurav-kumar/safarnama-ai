"""Place name -> (lat, lng), via OpenStreetMap's Nominatim.

Rules from Nominatim's usage policy, all enforced here:
  * an identifying User-Agent on every request
  * no more than one request per second (per process)
  * cache results -- repeats cost nothing

It fails soft. No network, a timeout, or no match returns None, and the map
simply shows fewer pins. Nothing about planning a trip depends on this.
"""
from __future__ import annotations

import logging
import math
import threading
import time
from dataclasses import dataclass

import httpx

from app.core.cache import get_cache
from app.core.config import settings

logger = logging.getLogger(__name__)

MIN_SECONDS_BETWEEN_REQUESTS = 1.1
REQUEST_TIMEOUT_SECONDS = 6
HIT_TTL = 30 * 24 * 3600      # places do not move
MISS_TTL = 24 * 3600          # but a miss may be a transient spelling/data gap


@dataclass(frozen=True)
class Point:
    lat: float
    lng: float


class GeocoderUnavailable(Exception):
    """The service could not be reached at all -- callers stop asking for the
    rest of this batch rather than wait out one timeout per place."""


_rate_lock = threading.Lock()
_last_request_at = 0.0


def _throttle() -> None:
    global _last_request_at
    with _rate_lock:
        wait = MIN_SECONDS_BETWEEN_REQUESTS - (time.monotonic() - _last_request_at)
        if wait > 0:
            time.sleep(wait)
        _last_request_at = time.monotonic()


def _fetch(query: str) -> list[dict]:
    """One HTTP call. Kept separate so tests replace only this."""
    _throttle()
    response = httpx.get(
        settings.GEOCODER_URL,
        params={"q": query, "format": "jsonv2", "limit": 1, "countrycodes": "in"},
        headers={"User-Agent": settings.GEOCODER_USER_AGENT, "Accept-Language": "en"},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()


def geocode(query: str) -> Point | None:
    key = "geo:" + " ".join(query.lower().split())
    cache = get_cache()

    cached = cache.get(key)
    if cached is not None:
        return Point(**cached) if cached else None  # {} is a cached miss

    try:
        results = _fetch(query)
    except httpx.HTTPStatusError as exc:
        # The service answered but refused (e.g. 429). Treat as unavailable for
        # now; do not cache, so it is retried later.
        raise GeocoderUnavailable(str(exc)) from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise GeocoderUnavailable(str(exc)) from exc

    if not results:
        cache.set(key, {}, MISS_TTL)
        return None

    point = Point(lat=float(results[0]["lat"]), lng=float(results[0]["lon"]))
    cache.set(key, {"lat": point.lat, "lng": point.lng}, HIT_TTL)
    return point


def distance_km(a: Point, b: Point) -> float:
    """Great-circle distance (haversine)."""
    r = 6371.0
    dlat = math.radians(b.lat - a.lat)
    dlng = math.radians(b.lng - a.lng)
    h = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(a.lat)) * math.cos(math.radians(b.lat)) * math.sin(dlng / 2) ** 2
    )
    return 2 * r * math.asin(math.sqrt(h))


# ---------------------------------------------------------------------------
# Place search for the destination picker (several results, with names)
# ---------------------------------------------------------------------------

SEARCH_TTL = 7 * 24 * 3600


@dataclass(frozen=True)
class Place:
    name: str          # short label, e.g. "Jaipur"
    label: str         # full address line from OSM
    lat: float
    lng: float
    kind: str          # OSM type, e.g. "city", "administrative"


def _place_from(row: dict) -> Place:
    address = row.get("address") or {}
    name = (
        row.get("name")
        or address.get("city")
        or address.get("town")
        or address.get("village")
        or address.get("state")
        or row.get("display_name", "").split(",")[0]
    )
    return Place(
        name=name,
        label=row.get("display_name", name),
        lat=float(row["lat"]),
        lng=float(row["lon"]),
        kind=row.get("addresstype") or row.get("type") or "",
    )


def _nominatim(path: str, params: dict) -> list[dict] | dict:
    _throttle()
    url = settings.GEOCODER_URL.rsplit("/", 1)[0] + "/" + path
    response = httpx.get(
        url,
        params={"format": "jsonv2", "addressdetails": 1, **params},
        headers={"User-Agent": settings.GEOCODER_USER_AGENT, "Accept-Language": "en"},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()


def search_places(query: str, limit: int = 6) -> list[Place]:
    """Up to `limit` matches for a free-text query, anywhere in the world."""
    q = " ".join(query.split())
    key = f"geo-search:{limit}:{q.lower()}"
    cache = get_cache()
    cached = cache.get(key)
    if cached is not None:
        return [Place(**p) for p in cached]

    try:
        rows = _nominatim("search", {"q": q, "limit": limit})
    except (httpx.HTTPError, ValueError) as exc:
        raise GeocoderUnavailable(str(exc)) from exc

    places = [_place_from(r) for r in rows] if isinstance(rows, list) else []
    cache.set(key, [p.__dict__ for p in places], SEARCH_TTL)
    return places


def reverse_place(lat: float, lng: float) -> Place | None:
    """The named place at a point (used when the map is clicked)."""
    key = f"geo-rev:{lat:.3f},{lng:.3f}"
    cache = get_cache()
    cached = cache.get(key)
    if cached is not None:
        return Place(**cached) if cached else None

    try:
        row = _nominatim("reverse", {"lat": lat, "lon": lng, "zoom": 10})
    except (httpx.HTTPError, ValueError) as exc:
        raise GeocoderUnavailable(str(exc)) from exc

    if not isinstance(row, dict) or "lat" not in row:
        cache.set(key, {}, MISS_TTL)
        return None
    place = _place_from(row)
    cache.set(key, place.__dict__, SEARCH_TTL)
    return place


def search_indian_places(query: str, limit: int = 5) -> list[dict]:
    """India-only fallback for towns missing from the static city list."""
    q = " ".join(query.split())
    key = f"geo-in:{limit}:{q.lower()}"
    cache = get_cache()
    cached = cache.get(key)
    if cached is not None:
        return cached
    try:
        rows = _nominatim("search", {"q": q, "limit": limit, "countrycodes": "in"})
    except (httpx.HTTPError, ValueError) as exc:
        raise GeocoderUnavailable(str(exc)) from exc
    out: list[dict] = []
    for r in rows if isinstance(rows, list) else []:
        a = r.get("address") or {}
        name = r.get("name") or a.get("city") or a.get("town") or a.get("village")
        state = a.get("state") or a.get("union_territory") or a.get("state_district")
        if name and state and not any(o["name"] == name and o["state"] == state for o in out):
            out.append({"name": name, "state": state, "label": f"{name}, {state}"})
    cache.set(key, out, SEARCH_TTL)
    return out
