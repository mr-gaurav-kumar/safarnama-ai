"""Budget Recommender (Phase 8, model #1): "I have INR X for N days -- where?"

Every destination in destination_features is scored on three things:

  style   cosine similarity between what the traveller wants and what the
          place is good for (five styles: adventure, relax, culture, food,
          nature). The traveller's vector is the styles they picked, nudged by
          their own rated trips: a 5-star trip pulls its styles up, a 1-star
          trip pushes them down. That is the same memory the planner uses.
  budget  does the money stretch? A quarter of the budget is set aside for
          getting there; the rest, per person per day, is compared with the
          place's typical on-ground cost. Places under 70% of what they need
          are left out rather than ranked low.
  season  if a month is given, the season model's reading for that place and
          month (app/ml/season.py). Places whose main draw is closed that
          month (park core zones in the monsoon) are left out.

  score = 0.55 * style + 0.25 * budget + 0.20 * season

Costs and styles are curated estimates (app/data/destinations.py), and the
response says so.
"""
from __future__ import annotations

import calendar
import uuid
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.data.destinations import STYLES, where
from app.ml import season
from app.ml.features import all_destinations, cosine, match, style_vector
from app.models.destination import DestinationFeature

TRAVEL_SHARE = 0.25
MIN_FIT = 0.7
WEIGHTS = {"style": 0.55, "budget": 0.25, "season": 0.20}
SEASON_SCORE = {"ideal": 1.0, "pleasant": 0.8, "hot": 0.35, "rainy": 0.35, "cold": 0.3}
VISITED_PENALTY = 0.1
CURATED_NOTE = ("Costs and styles are curated estimates, not official figures — "
                "check current prices before you book.")


@dataclass
class Taste:
    vector: list[float]
    notes: list[str] = field(default_factory=list)
    visited: set[str] = field(default_factory=set)


def _one_hot(tags: list[str]) -> list[float]:
    return [1.0 if s in tags else 0.0 for s in STYLES]


def taste_for(db: Session, user_id: uuid.UUID | None, style_tags: list[str],
              rows: list[DestinationFeature]) -> Taste:
    """The traveller's style vector: picked styles + what their ratings say."""
    from app.models.group import TripFeedback
    from app.models.trip import Trip

    base = _one_hot(style_tags)
    taste = Taste(vector=base)
    if user_id is None:
        return taste

    trips = db.scalars(select(Trip).where(Trip.user_id == user_id)).all()
    ratings = dict(db.execute(
        select(TripFeedback.trip_id, TripFeedback.rating).where(TripFeedback.user_id == user_id)
    ).all())

    pull = [0.0] * len(STYLES)
    rated = 0
    for t in trips:
        place = match(rows, t.destination)
        if place is not None:
            taste.visited.add(place.name)
        rating = ratings.get(t.id)
        if rating is None:
            continue
        weight = (rating - 3) / 2  # 5 -> +1, 4 -> +0.5, 3 -> 0, 2 -> -0.5, 1 -> -1
        if weight == 0:
            continue
        vec = _one_hot(list(t.style_tags or []))
        if place is not None:
            vec = [0.5 * a + 0.5 * b for a, b in zip(vec, style_vector(place))]
        pull = [p + weight * v for p, v in zip(pull, vec)]
        rated += 1
        word = "liked" if weight > 0 else "did not enjoy"
        taste.notes.append(f"You {word} {t.destination} ({rating}/5)")

    if rated:
        taste.vector = [max(0.0, b + 0.5 * p / rated) for b, p in zip(base, pull)]
    return taste


def _style_words(row: DestinationFeature, wanted: list[float]) -> str:
    vec = style_vector(row)
    if any(wanted):
        strong = [s for s, w, v in zip(STYLES, wanted, vec) if w > 0 and v >= 0.7]
    else:
        strong = [s for s, v in sorted(zip(STYLES, vec), key=lambda p: -p[1])[:2]]
    if not strong:
        return ""
    return ("Strong on " if any(wanted) else "Known for ") + " and ".join(strong[:3])


# A short trip spent mostly on the road is a worse trip: places this far
# (by road) move down for trips of this many days or fewer.
LONG_HAUL_KM = 700
SHORT_TRIP_DAYS = 3
LONG_HAUL_PENALTY = 0.08


def recommend(
    db: Session, *, budget: float, days: int, travelers: int, style_tags: list[str],
    month: int | None = None, user_id: uuid.UUID | None = None, limit: int = 6,
    origin: tuple[float, float] | None = None, only: set[str] | None = None, anchor: str | None = None,
) -> dict:
    """Rank destinations for this budget.

    origin  -- where the traveller starts. With it, each place is priced with
               its own fare there and back (by distance and likely mode)
               instead of a flat share of the budget, so nearby places get
               more money on the ground.
    only    -- limit to these destination names (a state, or near a place).
    anchor  -- the place the traveller asked for; listed first.
    """
    from app.assistant.estimate import ISLANDS, distance_km, estimate, travel_cost

    rows = all_destinations(db)
    if only is not None:
        rows = [r for r in rows if r.name in only]
    per_person_day = budget / travelers / days
    on_ground = per_person_day * (1 - TRAVEL_SHARE)
    taste = taste_for(db, user_id, style_tags, rows)
    wanted = taste.vector if any(taste.vector) else [1.0] * len(STYLES)

    seasons: dict[str, tuple[str, float]] = {}
    if month is not None:
        preds = season.predict_many([(r.lat, r.lng, r.altitude_m, r.coastal) for r in rows], month)
        seasons = {r.name: p for r, p in zip(rows, preds)}

    items: list[dict] = []
    over_budget = closed = 0
    for row in rows:
        km = mode = fare = None
        ground = on_ground
        if origin is not None:
            km = distance_km(origin, (row.lat, row.lng))
            if km < 40 and row.name != anchor:
                continue  # your own city is not a trip
            mode, fare = travel_cost(km, row.name in ISLANDS)
            ground = max(0.0, (budget / travelers - fare) / days)
        fit = ground / row.daily_cost
        if fit < MIN_FIT and row.name != anchor:
            over_budget += 1
            continue
        if month is not None and month in (row.closed_months or []):
            closed += 1
            continue

        style = cosine(wanted, style_vector(row))
        money = min(1.0, fit) ** 2
        reasons = []
        words = _style_words(row, taste.vector)
        if words:
            reasons.append(words)
        reasons.append(
            f"About ₹{row.daily_cost:,}/person/day there; you have ₹{ground:,.0f}"
            + (" after travel" if origin is not None else "")
            + (" — room to spare" if fit >= 1.3 else " — a bit tight" if fit < 1 else "")
        )
        season_label = season_conf = None
        if month is not None:
            season_label, season_conf = seasons[row.name]
            when = SEASON_SCORE[season_label]
            reasons.append(f"{calendar.month_name[month]} is {season_label} {where(row.region)}")
        else:
            when = 1.0

        score = WEIGHTS["style"] * style + WEIGHTS["budget"] * money + WEIGHTS["season"] * when
        if row.name in taste.visited:
            score -= VISITED_PENALTY
            reasons.append("You have been here before")
        if km is not None and km * 1.25 > LONG_HAUL_KM and days <= SHORT_TRIP_DAYS and row.name != anchor:
            score -= LONG_HAUL_PENALTY
            reasons.append(f"A long journey ({round(km * 1.25):,} km by road) for a {days}-day trip")
        est = None
        if origin is not None:
            e = estimate(daily_cost=row.daily_cost, days=days, travelers=travelers, budget=budget,
                         origin=origin, dest=(row.lat, row.lng), name=row.name)
            est = {"total": e.total, "verdict": e.verdict, "travel": e.travel, "stay": e.stay,
                   "food": e.food, "local": e.local}

        items.append({
            "name": row.name, "state": row.state, "blurb": row.blurb,
            "score": round(score, 3),
            "style_match": round(style, 3),
            "budget_fit": round(fit, 2),
            "daily_cost": row.daily_cost,
            "season": season_label, "season_confidence": season_conf,
            "styles": {s: row.styles.get(s, 0) for s in STYLES},
            "reasons": reasons,
            "visited": row.name in taste.visited,
            "distance_km": round(km) if km is not None else None,
            "travel_mode": mode,
            "travel_fare": int(fare) if fare is not None else None,
            "estimate": est,
            "is_destination": row.name == anchor,
        })

    # The place they asked for first, then everything else by score.
    items.sort(key=lambda i: (not i["is_destination"], -i["score"]))
    return {
        "per_person_per_day": round(per_person_day),
        "on_ground_per_day": round(on_ground),
        "travel_share": TRAVEL_SHARE,
        "considered": len(rows),
        "over_budget": over_budget,
        "closed": closed,
        "taste": taste.notes,
        "items": items[:limit],
        "note": CURATED_NOTE,
    }
