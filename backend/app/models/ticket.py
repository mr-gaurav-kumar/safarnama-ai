"""Tickets a traveller bought anywhere -- IRCTC, an airline, redBus, a hotel
site -- saved here so they are in one place.

The booking reference (PNR) and any attached e-ticket are encrypted with
the same vault key as My documents; everything else is plain so it can be
listed and sorted.
"""
import datetime as dt
import uuid

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin

MODES = ("train", "flight", "bus", "hotel", "other")


class Ticket(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "tickets"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    # Optional: the trip this ticket is for, so it shows on the trip page too.
    trip_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("trips.id", ondelete="SET NULL"), nullable=True, index=True,
    )
    mode: Mapped[str] = mapped_column(String(10), nullable=False)
    # Train name / airline / bus operator / hotel name
    provider: Mapped[str | None] = mapped_column(String(80), nullable=True)
    # Train no. / flight no. / bus or ticket no. / room type
    number: Mapped[str | None] = mapped_column(String(30), nullable=True)
    pnr_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    from_place: Mapped[str | None] = mapped_column(String(120), nullable=True)
    to_place: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # Departure / check-in, and arrival / check-out (local time, as printed on the ticket)
    depart_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    arrive_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    seat: Mapped[str | None] = mapped_column(String(60), nullable=True)  # coach/berth, seat, gate, room
    travel_class: Mapped[str | None] = mapped_column(String(30), nullable=True)
    passengers: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    fare: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Train only: the last PNR status we fetched
    status: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status_checked_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Encrypted e-ticket (PDF / photo) in PRIVATE_DOCS_DIR
    file_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    file_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
