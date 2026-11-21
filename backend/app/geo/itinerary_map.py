"""Put coordinates on an itinerary so the frontend can draw it on a map."""
from __future__ import annotations

import copy
import logging
from typing import Any

from app.core.config import settings
from app.geo.geocode import GeocoderUnavailable, Point, distance_km, geocode

logger = logging.getLogger(__name__)

# Nominatim allows one request a second. Past this many distinct places a plan
# would take minutes to map, so the rest are left without pins.
MAX_PLACES = 25


def add_coordinates(destination: str, day_plan: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return a copy of `day_plan` with `lat`/`lng` on every item that could be
    placed. Never raises; an item that cannot be placed simply has no pin."""
    plan = copy.deepcopy(day_plan)
    if not settings.GEOCODING_ENABLED or not plan:
        return plan

    try:
        centre = geocode(f"{destination}, India")
    except GeocoderUnavailable as exc:
        logger.info("Geocoder unreachable, no map for %s: %s", destination, exc)
        return plan
    if centre is None:
        return plan

    located: dict[str, Point | None] = {}
    for day in plan:
        for item in day.get("items", []):
            place = str(item.get("place", "")).strip()
            if not place:
                continue

            if place not in located:
                if len(located) >= MAX_PLACES:
                    continue
                located[place] = _locate(place, destination, centre)
                if located[place] is _UNAVAILABLE:
                    return _apply(plan, located)

            point = located[place]
            if isinstance(point, Point):
                item["lat"], item["lng"] = round(point.lat, 6), round(point.lng, 6)
    return plan


_UNAVAILABLE = object()


def _locate(place: str, destination: str, centre: Point):
    # The plain destination (what the fallback planner writes) is the centre.
    if place.lower() == destination.lower():
        return centre
    try:
        point = geocode(f"{place}, {destination}, India")
    except GeocoderUnavailable:
        return _UNAVAILABLE
    if point is None:
        return None
    if distance_km(point, centre) > settings.GEOCODE_MAX_KM_FROM_DESTINATION:
        # Almost always a same-named place elsewhere in India.
        logger.info("Dropping %s: %.0f km from %s", place, distance_km(point, centre), destination)
        return None
    return point


def _apply(plan: list[dict[str, Any]], located: dict) -> list[dict[str, Any]]:
    """The geocoder went away mid-run: keep the pins found so far."""
    for day in plan:
        for item in day.get("items", []):
            point = located.get(str(item.get("place", "")).strip())
            if isinstance(point, Point):
                item["lat"], item["lng"] = round(point.lat, 6), round(point.lng, 6)
    return plan
