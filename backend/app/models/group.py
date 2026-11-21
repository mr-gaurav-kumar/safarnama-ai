"""Group trips (§4.10) and feedback (§4.11).

The trip's owner is `trips.user_id`; everyone else on a trip has a row here.
"""
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON, CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin

JSONColumn = JSON().with_variant(postgresql.JSONB, "postgresql")


class TripCollaborator(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "trip_collaborators"
    __table_args__ = (UniqueConstraint("trip_id", "invited_email"),)

    trip_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("trips.id", ondelete="CASCADE"), index=True, nullable=False,
    )
    # Invitations go to an email address, which may not have an account yet.
    # `user_id` is filled in when that person joins.
    invited_email: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=True,
    )
    # invited | joined | declined
    status: Mapped[str] = mapped_column(String(10), default="invited", nullable=False)
    # SHA-256 of the join link's token; only the invited address can use it.
    invite_token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    invited_by: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
    )
    # This member's own preferences, merged with everyone else's when planning.
    style_tags: Mapped[list[str]] = mapped_column(JSONColumn, default=list, nullable=False)
    joined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TripRoomMessage(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "trip_room_messages"

    trip_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("trips.id", ondelete="CASCADE"), index=True, nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)


class TripFeedback(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "trip_feedback"
    __table_args__ = (
        UniqueConstraint("trip_id", "user_id"),
        CheckConstraint("rating BETWEEN 1 AND 5", name="ck_trip_feedback_rating"),
    )

    trip_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("trips.id", ondelete="CASCADE"), index=True, nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)


class TripMatchRequest(UUIDMixin, TimestampMixin, Base):
    """"Suggest teaming up" sent from one trip's owner to another's. One per
    pair, ever, so nobody can be spammed through this."""

    __tablename__ = "trip_match_requests"
    __table_args__ = (UniqueConstraint("from_trip_id", "to_trip_id"),)

    from_trip_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("trips.id", ondelete="CASCADE"), nullable=False,
    )
    to_trip_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("trips.id", ondelete="CASCADE"), index=True, nullable=False,
    )
    from_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False,
    )
