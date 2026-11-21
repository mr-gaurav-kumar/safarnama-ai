"""Think on the Plan (Phase 8, model #2).

Before the planner writes a single day, it thinks the trip through -- the way
a good travel agent would -- and shows its working:

  1. Where is this?        the destination, matched in destination_features;
                           failing that, the nearest known place (by map) or
                           one in the same state, said out loud.
  2. What is it like then? the season model (app/ml/season.py) for every month
                           the trip touches, with its confidence; plus parks
                           that are shut that month.
  3. How busy?             official monthly foreign-arrival figures (tourism.py)
                           and the two holiday rushes everyone knows about.
  4. Does the money work?  budget per person per day vs the place's typical cost.
  5. Does it suit them?    their chosen styles vs what the place is good for.

The result goes three places: the progress stream (the "Thinking" step the
traveller watches), the planner's prompt (as concrete instructions), and the
saved itinerary (the "How we thought about it" card).
"""
from __future__ import annotations

import calendar
import logging
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.core.config import settings
from app.data import tourism
from app.data.destinations import REGION_NAMES, where
from app.ml import season
from app.ml.budget_recommender import TRAVEL_SHARE
from app.ml.features import all_destinations, match
from app.models.destination import DestinationFeature

logger = logging.getLogger(__name__)

NEARBY_KM = 250
HILL_REGIONS = {"himalaya_hills", "himalaya_foothills", "ghats_hills"}

MONTHS = tuple(calendar.month_name[1:])
SEASON_LINES = {
    "ideal": "one of the best times to go",
    "pleasant": "a good time to go",
    "hot": "hot — expect harsh midday heat",
    "rainy": "monsoon season — expect heavy or frequent rain",
    "cold": "cold — snow and closed roads are possible",
}
SEASON_NOTES = {
    "hot": "It will be hot: put outdoor sightseeing before 11:00 and after 16:00, "
           "with indoor or shaded stops (museums, cafes, malls) in the middle of the day.",
    "rainy": "It is monsoon: give each day an indoor or covered backup, keep boat, beach and "
             "trek items optional, and avoid long hill drives after dark.",
    "cold": "It will be cold: start later in the morning, keep evenings indoors, and do not "
            "rely on high passes or remote roads being open.",
}


def _locate(db: Session, destination: str) -> tuple[DestinationFeature | None, dict | None, str]:
    """(row to borrow features from, override coords or None, how it was found)."""
    rows = all_destinations(db)
    row = match(rows, destination)
    if row is not None:
        return row, None, "matched"

    if settings.GEOCODING_ENABLED:
        try:
            from app.geo.geocode import Point, distance_km, geocode

            point = geocode(f"{destination}, India")
        except Exception:  # noqa: BLE001 -- thinking must never stop a plan
            point = None
        if point is not None:
            nearest = min(rows, key=lambda r: distance_km(point, Point(r.lat, r.lng)))
            if distance_km(point, Point(nearest.lat, nearest.lng)) <= NEARBY_KM:
                return nearest, {"lat": point.lat, "lng": point.lng}, "nearby"

    state = tourism.state_for(destination)
    if state:
        same = [r for r in rows if r.state == state]
        if same:
            return same[0], None, "state"
    return None, None, "unknown"


def _months(start: date, end: date) -> list[int]:
    seen: list[int] = []
    d = start
    while d <= end:
        if d.month not in seen:
            seen.append(d.month)
        d = (d.replace(day=1) + timedelta(days=32)).replace(day=1)
    return seen


def _overlaps(start: date, end: date, a: date, b: date) -> bool:
    return start <= b and a <= end


def _holiday_notes(start: date, end: date, region: str | None) -> list[str]:
    notes = []
    for year in {start.year, end.year}:
        if _overlaps(start, end, date(year, 12, 22), date(year + 1, 1, 2)) or \
           _overlaps(start, end, date(year - 1, 12, 22), date(year, 1, 2)):
            notes.append("Christmas–New Year week: the busiest and priciest stretch of the year — "
                         "book stays early.")
            break
    if region in HILL_REGIONS and any(
        _overlaps(start, end, date(y, 5, 15), date(y, 6, 30)) for y in {start.year, end.year}
    ):
        notes.append("Summer school holidays: hill stations are packed and roads jam at weekends.")
    return notes


def think_about_trip(
    db: Session, *, destination: str, start_date: date, end_date: date,
    budget: float, travelers: int, style_tags: list[str],
) -> dict:
    days = (end_date - start_date).days + 1
    row, coords, how = _locate(db, destination)
    thoughts: list[str] = []
    notes: list[str] = []
    months = _months(start_date, end_date)

    # 1. where
    place = None
    if row is not None:
        place = {"name": row.name, "state": row.state, "how": how,
                 "region": row.region, "region_name": REGION_NAMES.get(row.region, row.region)}
        if how == "nearby":
            thoughts.append(f"I don't know {destination} well, so I'm reading it like nearby {row.name}.")
        elif how == "state":
            thoughts.append(f"I don't know {destination} well; using {row.name} ({row.state}) as a rough guide.")
    else:
        thoughts.append(f"I couldn't place {destination} on my map, so I'm skipping the season and cost checks.")

    # 2. season
    seasons: list[dict] = []
    headline = f"Planning {days} day(s) in {destination}"
    if row is not None:
        lat = coords["lat"] if coords else row.lat
        lng = coords["lng"] if coords else row.lng
        preds = season.predict_months(lat, lng, row.altitude_m, row.coastal, months)
        seasons = [{"month": m, "label": lbl, "confidence": conf} for m, (lbl, conf) in zip(months, preds)]
        main = seasons[0]
        headline = f"{MONTHS[main['month'] - 1]} {where(row.region)} is {SEASON_LINES[main['label']]}"
        sure = "" if main["confidence"] >= 0.7 else ", so treat this as a rough guide"
        thoughts.append(f"{headline} (season model: {main['confidence']:.0%} confident{sure}).")
        for s in seasons[1:]:
            if s["label"] != main["label"]:
                thoughts.append(f"The trip runs into {MONTHS[s['month'] - 1]}, which is {SEASON_LINES[s['label']]}.")
        for lbl in dict.fromkeys(s["label"] for s in seasons):
            if lbl in SEASON_NOTES:
                notes.append(SEASON_NOTES[lbl])
        shut = [m for m in months if m in (row.closed_months or [])]
        if shut:
            msg = (f"{row.name}'s main attraction (the park's core safari zones) is usually closed in "
                   f"{', '.join(MONTHS[m - 1] for m in shut)}.")
            thoughts.append(msg)
            notes.append(msg + " Do not plan core-zone safaris; suggest buffer zones or other sights.")

    # 3. crowds
    month = start_date.month
    busiest = sorted(range(12), key=lambda i: -tourism.FTA_MONTHLY_2025_LAKH[i])
    fta_rank = busiest.index(month - 1) + 1
    holidays = _holiday_notes(start_date, end_date, row.region if row else None)
    good_weather = bool(seasons) and seasons[0]["label"] in ("ideal", "pleasant")
    if holidays or (good_weather and fta_rank <= 4):
        crowd = "busy"
    elif seasons and seasons[0]["label"] in ("rainy", "hot") or fta_rank >= 9:
        crowd = "quiet"
    else:
        crowd = "average"
    crowd_line = {
        "busy": "Expect crowds: popular sights early in the day, and book ahead.",
        "average": "Crowds should be normal for the season.",
        "quiet": "It's a quieter time — fewer crowds and often lower prices.",
    }[crowd] if row is not None else {
        "busy": "Nationally this is a busy month for travel — book ahead.",
        "average": "Nationally this is an average month for travel.",
        "quiet": "Nationally this is a quieter month for travel.",
    }[crowd]
    thoughts.append(crowd_line)
    thoughts.extend(holidays)
    if crowd == "busy":
        notes.append("It will be busy: schedule the most popular sights first thing in the morning.")
    notes.extend(holidays)

    # 4. money
    per_person_day = budget / travelers / days
    on_ground = per_person_day * (1 - TRAVEL_SHARE)
    verdict = None
    if row is not None:
        fit = on_ground / row.daily_cost
        verdict = ("tight" if fit < 0.8 else "workable" if fit < 1.1
                   else "comfortable" if fit < 2 else "generous")
        thoughts.append({
            "tight": f"The budget is tight: about ₹{on_ground:,.0f} per person per day on the ground, "
                     f"where ₹{row.daily_cost:,} is typical. I'll lean on budget stays and local transport.",
            "workable": f"The budget works: about ₹{on_ground:,.0f} per person per day on the ground, "
                        f"close to the typical ₹{row.daily_cost:,}.",
            "comfortable": f"The budget is comfortable: about ₹{on_ground:,.0f} per person per day "
                           f"against a typical ₹{row.daily_cost:,}.",
            "generous": f"The budget is generous (₹{on_ground:,.0f} per person per day vs a typical "
                        f"₹{row.daily_cost:,}) — room for a special stay or experience.",
        }[verdict])
        notes.append({
            "tight": "Money is tight for this place: choose budget stays, public or shared transport and "
                     "free sights, and keep the total well inside the budget.",
            "workable": "Money is about right for mid-range choices; avoid premium extras.",
            "comfortable": "There is room for good mid-range stays and a paid experience or two.",
            "generous": "There is room for one premium stay or experience; still keep within the budget.",
        }[verdict])

    # 5. style
    strong: list[str] = []
    weak: list[str] = []
    if row is not None and style_tags:
        for tag in style_tags:
            score = float(row.styles.get(tag, 0))
            (strong if score >= 0.7 else weak if score < 0.4 else []).append(tag)
        subject = row.name if how == "matched" else f"Places like {row.name}"
        if strong:
            thoughts.append(f"{subject} {'is' if how == 'matched' else 'are'} a good fit for {' and '.join(strong)}.")
        if weak:
            thoughts.append(f"{subject} {'isn' if how == 'matched' else 'aren'}'t known for {' or '.join(weak)}, "
                            "so I'll look for the best options nearby.")
            notes.append(f"This place is not strong on {' or '.join(weak)}: find the best nearby "
                         f"options or a short day trip, and say so in the explanation.")

    return {
        "version": 1,
        "place": place,
        "headline": headline,
        "seasons": seasons,
        "crowd": crowd,
        "budget": {"per_person_per_day": round(per_person_day), "on_ground_per_day": round(on_ground),
                   "typical": row.daily_cost if row else None, "verdict": verdict},
        "style": {"strong": strong, "weak": weak},
        "thoughts": thoughts,
        "prompt_notes": notes,
        "model": "Random Forest season model + curated destination data",
    }


def prompt_context(thinking: dict | None) -> str | None:
    if not thinking or not thinking.get("prompt_notes"):
        return None
    return " ".join(thinking["prompt_notes"])
