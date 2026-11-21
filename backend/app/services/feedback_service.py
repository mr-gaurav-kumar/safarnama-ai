"""Rating a trip after it ends (§4.11) -- and feeding that back into memory.

The owner's rating and comment are written into the trip's embedded summary and
stored beside its vector, so retrieval weighs trips they loved up and trips they
disliked down, and the planner is told what they did not enjoy. Members' ratings
are recorded too, but memory is per person and this trip is the owner's memory.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.group import TripFeedback
from app.models.user import User
from app.rag import retrieval
from app.services.group_service import GroupError, trip_for

logger = logging.getLogger(__name__)


def today():
    return datetime.now(ZoneInfo(settings.APP_TIMEZONE)).date()


def rate(db: Session, user: User, trip_id: uuid.UUID, rating: int, comment: str | None) -> TripFeedback:
    trip, role = trip_for(db, user.id, trip_id)
    if trip.status != "completed":
        raise GroupError("This trip has no plan to rate")
    if trip.end_date >= today():
        raise GroupError(f"You can rate this trip once it's over (after {trip.end_date:%d %b %Y})")

    row = db.scalar(select(TripFeedback).where(
        TripFeedback.trip_id == trip.id, TripFeedback.user_id == user.id
    ))
    if row is None:
        row = TripFeedback(trip_id=trip.id, user_id=user.id, rating=rating)
        db.add(row)
    row.rating = rating
    row.comment = (comment or "").strip() or None
    db.commit()
    db.refresh(row)

    if role == "owner":
        # Re-embed with the rating in the text and on the row. A failure here
        # must not lose the rating itself.
        try:
            retrieval.store_trip_embedding(db, trip)
        except Exception:  # noqa: BLE001
            logger.exception("Could not re-embed trip %s after feedback", trip.id)
            db.rollback()
    return row


def summary(db: Session, user: User, trip_id: uuid.UUID) -> dict:
    trip, _ = trip_for(db, user.id, trip_id)
    mine = db.scalar(select(TripFeedback).where(
        TripFeedback.trip_id == trip.id, TripFeedback.user_id == user.id
    ))
    count, avg = db.execute(
        select(func.count(), func.avg(TripFeedback.rating)).where(TripFeedback.trip_id == trip.id)
    ).one()
    return {
        "can_rate": trip.status == "completed" and trip.end_date < today(),
        "mine": {"rating": mine.rating, "comment": mine.comment} if mine else None,
        "count": count,
        "average": round(float(avg), 1) if avg is not None else None,
    }
