"""Fraud and risk monitoring (§4.12) and the admin audit trail (§4.14)."""
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, Uuid
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin

JSONColumn = JSON().with_variant(postgresql.JSONB, "postgresql")


class ActivityEvent(UUIDMixin, TimestampMixin, Base):
    """One thing a user did that the risk scorer cares about."""

    __tablename__ = "activity_events"

    # Null for a failed login against an unknown address.
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=True,
    )
    # signup | login_ok | login_failed | trip_created | invite_sent | match_request
    kind: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    ip: Mapped[str | None] = mapped_column(String(45), index=True, nullable=True)
    trip_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)


class FraudFlag(UUIDMixin, TimestampMixin, Base):
    """§5.1 fraud_flags, plus the review state an admin works through."""

    __tablename__ = "fraud_flags"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False,
    )
    trip_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("trips.id", ondelete="SET NULL"), nullable=True,
    )
    reason: Mapped[str] = mapped_column(String(40), nullable=False)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    # What triggered it, for the reviewer: counts, window, IPs...
    details: Mapped[dict[str, Any]] = mapped_column(JSONColumn, default=dict, nullable=False)
    # open | resolved | dismissed
    status: Mapped[str] = mapped_column(String(10), default="open", index=True, nullable=False)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AdminAction(UUIDMixin, TimestampMixin, Base):
    """Every change an admin makes, so admin power is itself auditable."""

    __tablename__ = "admin_actions"

    admin_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True,
    )
    action: Mapped[str] = mapped_column(String(40), nullable=False)
    target_type: Mapped[str] = mapped_column(String(20), nullable=False)
    target_id: Mapped[str] = mapped_column(String(64), nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSONColumn, default=dict, nullable=False)
