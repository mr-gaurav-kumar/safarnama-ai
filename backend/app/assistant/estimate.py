"""A tentative trip budget: getting there and back, plus stay, food and local
costs on the ground. Rough on purpose, and labelled as such everywhere it
is shown -- it is for deciding where to go, not for booking.

  getting there  straight-line distance x 1.25 for roads, priced by the mode
                 a traveller would most likely use at that distance
  on the ground  the destination's typical cost per person per day (curated,
                 app/data/destinations.py), split into stay / food / local
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, timedelta

# Friday and Saturday nights: hotels in India typically charge about a
# quarter more, and popular places fill up.
WEEKEND_NIGHT_PREMIUM = 0.25

ISLANDS = {"Port Blair", "Havelock"}

# Big cities people travel FROM that are not destinations themselves.
ORIGINS: dict[str, tuple[float, float]] = {
    "ghaziabad": (28.67, 77.45), "noida": (28.54, 77.39), "gurugram": (28.46, 77.03), "gurgaon": (28.46, 77.03),
    "faridabad": (28.41, 77.32), "pune": (18.52, 73.86), "chandigarh": (30.73, 76.78), "indore": (22.72, 75.86),
    "bhopal": (23.26, 77.41), "patna": (25.59, 85.14), "nagpur": (21.15, 79.09), "surat": (21.17, 72.83),
    "kanpur": (26.45, 80.33), "vadodara": (22.31, 73.18), "ranchi": (23.34, 85.31), "dehradun": (30.32, 78.03),
    "meerut": (28.98, 77.71), "ludhiana": (30.90, 75.86), "raipur": (21.25, 81.63), "coimbatore": (11.02, 76.96),
    "thiruvananthapuram": (8.52, 76.94), "trivandrum": (8.52, 76.94), "guwahati": (26.14, 91.74),
    "new delhi": (28.61, 77.21), "bangalore": (12.97, 77.59), "bombay": (19.08, 72.88), "calcutta": (22.57, 88.36),
}


def distance_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lng1, lat2, lng2 = map(math.radians, (*a, *b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lng2 - lng1) / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


def travel_cost(km: float, island: bool) -> tuple[str, int]:
    """(likely mode, round-trip fare per person)."""
    road = km * 1.25
    if island or road > 1400:
        return "flight", round(2 * (3000 + 3.0 * km), -2)
    if road > 650:
        return "train (3AC) or flight", round(2 * (1.5 * road), -2)
    if road > 60:
        return "bus or train", round(2 * (1.6 * road + 150), -2)
    return "local cab / metro", 600


@dataclass
class Estimate:
    travel_mode: str | None
    travel: int | None  # all travellers, round trip; None when we don't know where they start
    stay: int
    food: int
    local: int
    total: int
    per_person: int
    verdict: str | None  # comfortable | fits | tight | over (None without a budget)
    distance_km: int | None
    start_date: str | None = None
    end_date: str | None = None
    nights: int = 0
    weekend_nights: int = 0


def estimate(
    *, daily_cost: int, days: int, travelers: int, budget: float | None,
    origin: tuple[float, float] | None, dest: tuple[float, float], name: str, start: date | None = None,
) -> Estimate:
    nights = max(days - 1, 1)  # no hotel on the last day
    ground = daily_cost * days * travelers
    per_night = ground * 0.45 / days
    weekend = 0
    if start is not None:
        # The night of each day is a "weekend night" when that day is a Friday or Saturday.
        weekend = sum(1 for i in range(nights) if (start + timedelta(days=i)).weekday() in (4, 5))
    stay = round(per_night * (nights + WEEKEND_NIGHT_PREMIUM * weekend), -2)
    food = round(ground * 0.32, -2)
    local = round(ground * 0.23, -2)
    mode = travel = km = None
    if origin is not None:
        km = distance_km(origin, dest)
        mode, fare = travel_cost(km, name in ISLANDS)
        travel = int(fare) * travelers
    total = int(stay + food + local + (travel or 0))
    verdict = None
    if budget:
        r = total / budget
        verdict = "comfortable" if r <= 0.85 else "fits" if r <= 1.0 else "tight" if r <= 1.15 else "over"
    return Estimate(
        travel_mode=mode, travel=travel, stay=int(stay), food=int(food), local=int(local), total=total,
        per_person=round(total / travelers), verdict=verdict, distance_km=round(km) if km is not None else None,
        start_date=start.isoformat() if start else None,
        end_date=(start + timedelta(days=days - 1)).isoformat() if start else None,
        nights=nights, weekend_nights=weekend,
    )
