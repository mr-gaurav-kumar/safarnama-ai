"""Trips and their generated itineraries -- §5.1 of the project document."""
import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Numeric, String, Text, Uuid
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

# JSONB on Postgres (indexable, binary) and plain JSON elsewhere, so the same
# models run against SQLite in development and tests.
JSONColumn = JSON().with_variant(postgresql.JSONB, "postgresql")


class Trip(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "trips"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        index=True, nullable=False,
    )

    destination: Mapped[str] = mapped_column(String(200), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    budget: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    travelers: Mapped[int] = mapped_column(nullable=False, default=1)

    # e.g. ["adventure", "food"] -- a list, not a comma string, so filtering
    # never has to parse text.
    style_tags: Mapped[list[str]] = mapped_column(JSONColumn, default=list, nullable=False)

    # Whether past-trip memory was used. Phase 2 reads this to decide whether to
    # run retrieval at all.
    use_memory: Mapped[bool] = mapped_column(default=True, nullable=False)

    # Generation lifecycle: processing -> completed | failed
    status: Mapped[str] = mapped_column(String(20), default="processing", nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Planning lifecycle (§4.16): draft -> saved -> upcoming -> completed
    plan_status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)

    # Where the plan came from: "ai" (the planner), "manual" (written by the
    # traveller) or "copy" (an earlier trip planned again on new dates).
    source: Mapped[str] = mapped_column(String(10), default="ai", server_default="ai", nullable=False)

    # Opt-in: may other travellers with overlapping dates to the same place see
    # this trip (owner's first name, destination, dates only) and suggest
    # teaming up? Off unless the owner turns it on.
    discoverable: Mapped[bool] = mapped_column(default=False, nullable=False)

    # Set when the pre-trip reminder goes out, so a restart or a second run of
    # the daily job never sends it twice.
    reminder_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    itinerary: Mapped["Itinerary | None"] = relationship(
        back_populates="trip", cascade="all, delete-orphan", uselist=False,
    )

    def __repr__(self) -> str:
        return f"<Trip {self.destination} {self.start_date}..{self.end_date}>"


class Itinerary(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "itineraries"

    trip_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("trips.id", ondelete="CASCADE"),
        unique=True, index=True, nullable=False,
    )

    # [{day, date, items: [{time, place, activity, estimated_cost}]}, ...]
    day_plan: Mapped[list[dict[str, Any]]] = mapped_column(JSONColumn, nullable=False)

    # {stay, food, travel, misc}
    budget_breakdown: Mapped[dict[str, Any]] = mapped_column(JSONColumn, nullable=False)

    # "Why this was suggested" -- written by the planner.
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)

    # The past trips retrieval fed into this plan, as structured data rather
    # than prose: [{trip_id, destination, start_date, similarity}]. The UI shows
    # these directly, so the explanation never depends on the model naming them.
    memory_sources: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONColumn, nullable=True
    )

    # "Think on the Plan" (Phase 8): what the planner weighed before writing
    # the plan -- season, crowds, budget, style fit. Null for older plans.
    thinking: Mapped[dict[str, Any] | None] = mapped_column(JSONColumn, nullable=True)

    trip: Mapped[Trip] = relationship(back_populates="itinerary")
