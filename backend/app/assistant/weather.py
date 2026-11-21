"""Weather for the assistant.

  season  -- what the month is usually like there: the Random Forest season
             model behind Think on the Plan. Works for any month, offline.
  live    -- the actual forecast for the next week, when the trip is this
             month: Open-Meteo (free, no API key). Off in tests; any failure
             just means no live forecast.
"""
from __future__ import annotations

import logging
from datetime import date
from functools import lru_cache

from app.core.config import settings
from app.ml import season

logger = logging.getLogger(__name__)

SEASON_TEXT = {
    "ideal": "one of the best times to go",
    "pleasant": "pleasant — a good time to go",
    "hot": "hot — harsh midday heat",
    "rainy": "monsoon — heavy or frequent rain",
    "cold": "cold — snow and closed roads are possible",
}
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


def season_for(lat: float, lng: float, altitude_m: int, coastal: bool, month: int) -> dict:
    label, conf = season.predict(lat, lng, altitude_m, coastal, month)
    return {"label": label, "text": SEASON_TEXT.get(label, label), "confidence": round(conf, 2)}


@lru_cache(maxsize=256)
def _forecast_cached(lat: float, lng: float, day: str) -> tuple | None:
    import httpx

    r = httpx.get(
        FORECAST_URL,
        params={
            "latitude": lat, "longitude": lng, "timezone": "Asia/Kolkata", "forecast_days": 7,
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
        },
        timeout=4,
    )
    r.raise_for_status()
    d = r.json()["daily"]
    return tuple(zip(d["time"], d["temperature_2m_max"], d["temperature_2m_min"], d["precipitation_probability_max"]))


def live_forecast(lat: float, lng: float) -> dict | None:
    """Next 7 days: highs, lows and the rainiest day. None if unavailable."""
    if not settings.LIVE_WEATHER_ENABLED:
        return None
    try:
        rows = _forecast_cached(round(lat, 2), round(lng, 2), date.today().isoformat())
    except Exception:  # noqa: BLE001 -- a forecast is a nicety
        logger.info("Live forecast unavailable for %s,%s", lat, lng)
        return None
    if not rows:
        return None
    highs = [r[1] for r in rows if r[1] is not None]
    lows = [r[2] for r in rows if r[2] is not None]
    rain = [r[3] or 0 for r in rows]
    if not highs or not lows:
        return None
    return {
        "high": round(max(highs)), "low": round(min(lows)), "rain_chance": max(rain),
        "rainy_days": sum(1 for x in rain if x >= 50), "days": len(rows), "source": "Open-Meteo forecast",
    }
