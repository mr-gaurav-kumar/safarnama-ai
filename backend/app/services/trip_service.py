"""Everything that reads or writes trips.

Every query is scoped by user_id. A trip is never fetched by id alone, so one
user cannot reach another's trip by guessing a UUID.
"""
import logging
import uuid
from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.data import tourism
from app.geo.itinerary_map import add_coordinates
from app.llm import generate_itinerary
from app.llm.itinerary import ItineraryGenerationError
from app.ml.think import prompt_context as think_prompt_context
from app.models.trip import Itinerary, Trip
from app.rag import retrieval
from app.schemas.trip import TripCreate

logger = logging.getLogger(__name__)


class TripNotFound(Exception):
    pass


def list_trips(db: Session, *, user_id: uuid.UUID) -> list[Trip]:
    return list(
        db.scalars(
            select(Trip).where(Trip.user_id == user_id).order_by(Trip.created_at.desc())
        )
    )


def get_trip(db: Session, *, user_id: uuid.UUID, trip_id: uuid.UUID) -> Trip:
    trip = db.scalar(
        select(Trip)
        .where(Trip.id == trip_id, Trip.user_id == user_id)
        .options(selectinload(Trip.itinerary))
    )
    if trip is None:
        # Deliberately the same error whether the trip does not exist or belongs
        # to someone else -- otherwise this leaks which ids are real.
        raise TripNotFound(str(trip_id))
    return trip


def delete_trip(db: Session, *, user_id: uuid.UUID, trip_id: uuid.UUID) -> None:
    trip = get_trip(db, user_id=user_id, trip_id=trip_id)
    db.delete(trip)
    db.commit()


# progress(step, message) -- or progress(step, message, thoughts) for the
# "thinking" step, which carries the planner's reasoning as a list of lines.
ProgressFn = Callable[..., None]


def _no_progress(_step: str, _message: str, _thoughts: list[str] | None = None) -> None:
    pass


def create_trip(db: Session, *, user_id: uuid.UUID, payload: TripCreate) -> Trip:
    """Save the request with status 'processing' and return straight away.

    Generation is a separate job (`app.tasks.jobs.run_trip_generation`) so the
    request never waits on retrieval or the LLM.
    """
    trip = Trip(
        user_id=user_id,
        destination=payload.destination.strip(),
        start_date=payload.start_date,
        end_date=payload.end_date,
        budget=payload.budget,
        travelers=payload.travelers,
        style_tags=list(payload.style_tags),
        use_memory=payload.use_memory,
        status="processing",
    )
    db.add(trip)
    db.commit()
    db.refresh(trip)
    return trip


def attach_itinerary(db: Session, trip: Trip, progress: ProgressFn = _no_progress) -> Trip:
    """Retrieve, generate, store -- the whole RAG loop for one trip.

    1. Retrieval: if the trip asks for it, find the user's most similar past
       trips in their embedded memory.
    2. Augmentation + generation: hand those to the planner with the request.
    3. Persist: save the plan, then embed this trip so it becomes memory for
       the next one.

    Safe to call again on the same trip -- it replaces the plan and the
    embedding rather than duplicating them.
    """
    progress("started", "Reading your request…")
    from app.services.group_service import group_preferences

    group = group_preferences(db, trip)

    hits: list[retrieval.MemoryHit] = []
    if trip.use_memory:
        progress("retrieving", "Looking through your past trips…")
        hits = retrieval.find_similar_trips(
            db,
            user_id=trip.user_id,
            query_text=retrieval.summarise_request(
                destination=trip.destination,
                start_date=trip.start_date,
                end_date=trip.end_date,
                style_tags=group.tags,
                budget=float(trip.budget),
            ),
            exclude_trip_id=trip.id,
        )

    # Think on the Plan: season, crowds, budget and fit, worked out before
    # writing -- shown to the traveller and handed to the planner as notes.
    thinking = None
    try:
        from app.ml.think import think_about_trip

        thinking = think_about_trip(
            db, destination=trip.destination, start_date=trip.start_date,
            end_date=trip.end_date, budget=float(trip.budget),
            travelers=trip.travelers, style_tags=group.tags,
        )
        progress("thinking", thinking["headline"], thinking["thoughts"])
    except Exception:  # noqa: BLE001 -- thinking is a help, never a blocker
        logger.exception("Thinking step failed for trip %s", trip.id)
        db.rollback()

    progress("generating", "Planning your days…")
    try:
        plan = generate_itinerary(
            destination=trip.destination,
            start_date=trip.start_date,
            end_date=trip.end_date,
            budget=float(trip.budget),
            travelers=trip.travelers,
            style_tags=group.tags,
            memory_context=retrieval.build_memory_context(hits),
            group_context=group.context,
            govt_context=tourism.context_for_trip(trip.destination, trip.start_date.month),
            thinking_context=think_prompt_context(thinking),
        )
    except ItineraryGenerationError as exc:
        trip.status = "failed"
        trip.error = str(exc)
        db.commit()
        db.refresh(trip)
        return trip

    progress("mapping", "Finding places on the map…")
    try:
        day_plan = add_coordinates(trip.destination, plan.day_plan)
    except Exception:  # noqa: BLE001 -- a map is a nicety, never a failure
        logger.exception("Mapping failed for trip %s", trip.id)
        day_plan = plan.day_plan

    if trip.itinerary is not None:
        db.delete(trip.itinerary)
        db.flush()

    db.add(
        Itinerary(
            trip_id=trip.id,
            day_plan=day_plan,
            budget_breakdown=plan.budget_breakdown,
            explanation=plan.explanation,
            memory_sources=[
                {
                    "trip_id": str(h.trip_id),
                    "destination": h.destination,
                    "start_date": h.start_date.isoformat(),
                    "similarity": round(h.similarity, 3),
                }
                for h in hits
            ] or None,
            thinking=thinking,
        )
    )
    trip.status = "completed"
    trip.error = None
    db.commit()
    db.refresh(trip)

    # Memory grows: this trip is now retrievable for the next request. A failure
    # here must not lose a plan the user already has, so it is logged, not raised.
    progress("saving", "Saving to your travel memory…")
    try:
        retrieval.store_trip_embedding(db, trip)
    except Exception:  # noqa: BLE001
        logger.exception("Could not store the embedding for trip %s", trip.id)
        db.rollback()

    return trip
