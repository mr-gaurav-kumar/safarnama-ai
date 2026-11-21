"""Live train search via the RapidAPI "IRCTC" API (irctc1.p.rapidapi.com).

It is an unofficial API with a small free quota, so every answer is cached
(stations for a month, timetables for a few hours) and the shape of its
responses is read defensively -- a missing field becomes None, never a crash.
Booking always happens on irctc.co.in; this only searches.
"""
from __future__ import annotations

import logging
from datetime import date

import httpx

from app.core.cache import get_cache
from app.core.config import settings

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 12
STATION_TTL = 30 * 24 * 3600
TRAINS_TTL = 6 * 3600


class RailNotConfigured(Exception):
    """No RAPIDAPI_KEY in .env."""


class RailUnavailable(Exception):
    """The API refused, timed out, or ran out of free quota."""


def configured() -> bool:
    return bool(settings.RAPIDAPI_KEY)


def _get(path: str, params: dict) -> dict:
    if not configured():
        raise RailNotConfigured()
    host = settings.RAPIDAPI_IRCTC_HOST
    try:
        r = httpx.get(
            f"https://{host}{path}",
            params=params,
            headers={"x-rapidapi-key": settings.RAPIDAPI_KEY, "x-rapidapi-host": host},
            timeout=TIMEOUT_SECONDS,
        )
    except httpx.HTTPError as exc:
        raise RailUnavailable("Train search could not be reached") from exc
    if r.status_code == 429:
        raise RailUnavailable("The free train-search quota is used up for now. Try again later.")
    if r.status_code in (401, 403):
        raise RailUnavailable("The train-search key was refused. Check RAPIDAPI_KEY and the plan subscription.")
    if r.status_code >= 400:
        raise RailUnavailable(f"Train search failed ({r.status_code})")
    try:
        body = r.json()
    except ValueError as exc:
        raise RailUnavailable("Train search sent an unreadable answer") from exc
    if isinstance(body, dict) and body.get("status") is False:
        raise RailUnavailable(str(body.get("message") or "Train search returned no data"))
    return body if isinstance(body, dict) else {"data": body}


def _pick(d: dict, *keys: str):
    for k in keys:
        v = d.get(k)
        if v not in (None, ""):
            return v
    return None


def search_stations(query: str) -> list[dict]:
    q = " ".join(query.split())
    key = f"rail-st:{q.lower()}"
    cache = get_cache()
    cached = cache.get(key)
    if cached is not None:
        return cached
    body = _get("/api/v1/searchStation", {"query": q})
    out: list[dict] = []
    for row in body.get("data") or []:
        if not isinstance(row, dict):
            continue
        code = _pick(row, "code", "station_code", "stationCode")
        name = _pick(row, "eng_name", "name", "station_name", "stationName")
        if not code or not name:
            continue
        out.append({
            "code": str(code).upper(),
            "name": str(name).title() if str(name).isupper() else str(name),
            "state": _pick(row, "state_name", "state"),
        })
    cache.set(key, out, STATION_TTL)
    return out


def trains_between(src: str, dst: str, day: date) -> list[dict]:
    src, dst = src.upper().strip(), dst.upper().strip()
    key = f"rail-tb:{src}:{dst}:{day.isoformat()}"
    cache = get_cache()
    cached = cache.get(key)
    if cached is not None:
        return cached
    body = _get(
        "/api/v3/trainBetweenStations",
        {"fromStationCode": src, "toStationCode": dst, "dateOfJourney": day.isoformat()},
    )
    out: list[dict] = []
    for row in body.get("data") or []:
        if not isinstance(row, dict):
            continue
        number = _pick(row, "train_number", "trainNumber", "train_no")
        name = _pick(row, "train_name", "trainName")
        if not number:
            continue
        classes = _pick(row, "class_type", "classes", "avlClasses") or []
        run_days = _pick(row, "run_days", "runDays") or []
        out.append({
            "number": str(number),
            "name": str(name).title() if name and str(name).isupper() else name,
            "from_code": _pick(row, "from", "from_station_code") or src,
            "from_name": _pick(row, "from_station_name", "fromStnName"),
            "to_code": _pick(row, "to", "to_station_code") or dst,
            "to_name": _pick(row, "to_station_name", "toStnName"),
            "departs": _pick(row, "from_std", "from_sta", "departureTime"),
            "arrives": _pick(row, "to_sta", "to_std", "arrivalTime"),
            "arrives_day_offset": _pick(row, "to_day", "d_day") if isinstance(_pick(row, "to_day", "d_day"), int) else None,
            "duration": _pick(row, "duration", "travel_time"),
            "classes": [str(c) for c in classes] if isinstance(classes, list) else [],
            "run_days": [str(d) for d in run_days] if isinstance(run_days, list) else [],
            "train_type": _pick(row, "train_type", "trainType"),
        })
    cache.set(key, out, TRAINS_TTL)
    return out


# The PNR path on the same RapidAPI "irctc1" API. Kept in one place: if the
# provider renames it, change it here. Any failure is the caller's cue to
# send the traveller to the official enquiry page instead.
PNR_PATH = "/api/v3/getPNRStatus"


def pnr_status(pnr: str) -> str:
    """One line, e.g. "CNF B3 45 · chart prepared" or "WL 12 → RAC 3".
    Raises RailUnavailable when the service can't say."""
    body = _get(PNR_PATH, {"pnrNumber": pnr})
    data = body.get("data") if isinstance(body.get("data"), dict) else body
    people = (_pick(data, "PassengerStatus", "passengerList", "passengers") or [])
    if not isinstance(people, list) or not people:
        raise RailUnavailable("No passenger status in the answer")
    parts = []
    for p in people[:6]:
        if not isinstance(p, dict):
            continue
        now = _pick(p, "CurrentStatusNew", "CurrentStatus", "currentStatus", "currentStatusDetails")
        booked = _pick(p, "BookingStatusNew", "BookingStatus", "bookingStatus", "bookingStatusDetails")
        if now or booked:
            parts.append(str(now or booked) if not (now and booked and now != booked) else f"{booked} → {now}")
    if not parts:
        raise RailUnavailable("No passenger status in the answer")
    chart = _pick(data, "ChartPrepared", "chartStatus", "chartPrepared")
    line = ", ".join(parts)
    if chart in (True, "true", "Chart Prepared", "Y"):
        line += " (chart prepared)"
    return line
