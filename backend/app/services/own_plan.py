"""Plans the traveller writes, edits or reuses themselves -- no AI in the loop.

Three things a traveller can do without the planner:

  * write a plan from scratch and save it                     create_own_plan
  * change the days of a plan they own, AI-made or their own  replace_days
  * plan a trip again on new dates: the days, the notes and   copy_trip
    their own packing list come along, shifted to the new dates

A saved plan is an ordinary completed trip: it shows on the dashboard, exports
to PDF, has tickets and a packing list, and becomes memory for future AI plans.
The season reading ("Think on the Plan") is still worked out for it, because it
is local and quick and the PDF and packing suggestions use it.
"""
from __future__ import annotations

import copy
import logging
import uuid
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.packing import PackingItem
from app.models.trip import Itinerary, Trip
from app.schemas.packing import ItemIn
from app.schemas.trip import OwnPlanCreate, PlanDayIn

logger = logging.getLogger(__name__)


def build_day_plan(start: date, end: date, days: list[PlanDayIn]) -> list[dict]:
    """One entry per trip day, dated from `start`. Days the traveller left out
    are kept empty; extra days beyond the trip are dropped. Items run in time
    order, with untimed ones last."""
    n = (end - start).days + 1
    plan = []
    for i in range(n):
        items = days[i].items if i < len(days) else []
        rows = [
            {"time": it.time, "activity": it.activity, "place": it.place,
             "estimated_cost": float(it.estimated_cost)}
            for it in items
        ]
        rows.sort(key=lambda r: (r["time"] == "", r["time"]))
        plan.append({"day": i + 1, "date": (start + timedelta(days=i)).isoformat(), "items": rows})
    return plan


def _breakdown(day_plan: list[dict]) -> dict[str, float]:
    total = sum(float(i.get("estimated_cost") or 0) for d in day_plan for i in d.get("items", []))
    return {"activities": total} if total else {}


def _think(db: Session, trip: Trip) -> dict | None:
    try:
        from app.ml.think import think_about_trip

        thinking = think_about_trip(
            db, destination=trip.destination, start_date=trip.start_date, end_date=trip.end_date,
            budget=float(trip.budget) or 1.0, travelers=trip.travelers, style_tags=list(trip.style_tags or []),
        )
    except Exception:  # noqa: BLE001 -- the season is a help, never a blocker
        logger.exception("Thinking failed for saved plan %s", trip.id)
        db.rollback()
        return None
    if not float(trip.budget):
        # No budget given: a verdict on it would be made up.
        thinking["budget"]["verdict"] = None
        thinking["thoughts"] = [t for t in thinking.get("thoughts", []) if "budget" not in t.lower()]
    return thinking


def create_own_plan(db: Session, *, user_id: uuid.UUID, payload: OwnPlanCreate) -> Trip:
    trip = Trip(
        user_id=user_id,
        destination=payload.destination.strip(),
        start_date=payload.start_date,
        end_date=payload.end_date,
        budget=payload.budget,
        travelers=payload.travelers,
        style_tags=list(payload.style_tags),
        use_memory=False,
        status="completed",
        plan_status="saved",
        source="manual",
    )
    db.add(trip)
    db.flush()
    day_plan = build_day_plan(trip.start_date, trip.end_date, payload.days)
    db.add(Itinerary(
        trip_id=trip.id, day_plan=day_plan, budget_breakdown=_breakdown(day_plan),
        explanation=(payload.notes or None), memory_sources=None, thinking=_think(db, trip),
    ))
    db.commit()
    if payload.packing:
        set_packing(db, trip, user_id, payload.packing)
    db.refresh(trip)
    return trip


def set_packing(db: Session, trip: Trip, user_id: uuid.UUID, items: list[ItemIn]) -> None:
    """Make the traveller's own packing items match `items`. Matching is by
    name (any case), so an item that stays keeps its ticks. Items the admin
    added for everyone are never touched here."""
    wanted: dict[str, ItemIn] = {}
    for it in items:
        wanted.setdefault(it.name.casefold(), it)
    have = {
        p.name.casefold(): p
        for p in db.scalars(select(PackingItem).where(
            PackingItem.trip_id == trip.id, PackingItem.user_id == user_id, PackingItem.default_id.is_(None),
        ))
    }
    for key, p in have.items():
        if key not in wanted:
            db.delete(p)
    for key, it in wanted.items():
        p = have.get(key)
        if p is None:
            db.add(PackingItem(trip_id=trip.id, user_id=user_id, name=it.name, category=it.category,
                               quantity=it.quantity, source="mine"))
        else:
            p.name, p.category, p.quantity = it.name, it.category, it.quantity
    db.commit()


def replace_days(db: Session, trip: Trip, days: list[PlanDayIn], notes: str | None,
                 packing: list[ItemIn] | None = None, user_id: uuid.UUID | None = None) -> Trip:
    """Swap in the traveller's version of the days. An AI plan keeps its own
    budget categories; a plan the traveller wrote is re-totalled."""
    day_plan = build_day_plan(trip.start_date, trip.end_date, days)
    it = trip.itinerary
    if it is None:
        it = Itinerary(trip_id=trip.id, day_plan=day_plan, budget_breakdown=_breakdown(day_plan),
                       explanation=notes or None, thinking=_think(db, trip))
        db.add(it)
    else:
        it.day_plan = day_plan
        if trip.source != "ai" or not it.budget_breakdown:
            it.budget_breakdown = _breakdown(day_plan)
        if notes is not None:
            it.explanation = notes or None
    trip.status, trip.error = "completed", None
    db.commit()
    if packing is not None:
        set_packing(db, trip, user_id or trip.user_id, packing)
    db.refresh(trip)
    return trip


def copy_trip(db: Session, trip: Trip, *, user_id: uuid.UUID, start: date) -> Trip:
    """The same trip again from `start`: same length, the days moved to the
    new dates, and the requester's own packing list (unticked)."""
    shift = start - trip.start_date
    new = Trip(
        user_id=user_id,
        destination=trip.destination,
        start_date=start,
        end_date=trip.end_date + shift,
        budget=trip.budget,
        travelers=trip.travelers,
        style_tags=list(trip.style_tags or []),
        use_memory=trip.use_memory,
        status="completed",
        plan_status="saved",
        source="copy",
    )
    db.add(new)
    db.flush()

    old = trip.itinerary
    day_plan = copy.deepcopy(old.day_plan) if old else []
    for i, day in enumerate(day_plan):
        day["day"] = i + 1
        day["date"] = (start + timedelta(days=i)).isoformat()
    db.add(Itinerary(
        trip_id=new.id, day_plan=day_plan,
        budget_breakdown=dict(old.budget_breakdown or {}) if old else {},
        explanation=old.explanation if old else None,
        memory_sources=None, thinking=_think(db, new),
    ))

    # Admin defaults are added to every list on its own (packing_service.sync_defaults).
    for p in db.scalars(select(PackingItem).where(
        PackingItem.trip_id == trip.id, PackingItem.user_id == user_id, PackingItem.default_id.is_(None),
    )):
        db.add(PackingItem(trip_id=new.id, user_id=user_id, name=p.name, category=p.category,
                           quantity=p.quantity, source=p.source))
    db.commit()
    db.refresh(new)
    return new


def enrich(db: Session, trip: Trip) -> None:
    """After a save: map pins for the days, and the trip into travel memory.
    Both can be slow (geocoding) and both are optional, so they run after the
    response has gone."""
    from app.geo.itinerary_map import add_coordinates
    from app.rag import retrieval

    if trip.itinerary is not None:
        try:
            trip.itinerary.day_plan = add_coordinates(trip.destination, trip.itinerary.day_plan)
            db.commit()
        except Exception:  # noqa: BLE001
            logger.exception("Mapping failed for saved plan %s", trip.id)
            db.rollback()
    try:
        retrieval.store_trip_embedding(db, trip)
    except Exception:  # noqa: BLE001
        logger.exception("Could not store the embedding for saved plan %s", trip.id)
        db.rollback()
