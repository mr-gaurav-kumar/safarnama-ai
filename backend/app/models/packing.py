"""Packing lists: what each traveller carries on a trip, ticked off when they
pack to leave and again when they pack to come home.

Two tables:
  packing_defaults -- items the admin adds for everyone, or for one person.
                      They appear on every trip list of the people they target
                      and only the admin can remove them.
  packing_items    -- one traveller's list for one trip. Each person on a
                      group trip has their own list.
"""
import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin

CATEGORIES = ("clothes", "footwear", "toiletries", "documents", "electronics", "health", "accessories", "other")


class PackingDefault(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "packing_defaults"

    name: Mapped[str] = mapped_column(String(80), nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=False, default="other")
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    note: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # Null = every traveller; otherwise only this person.
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True,
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )


class PackingItem(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "packing_items"

    trip_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("trips.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=False, default="other")
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    # Ticked when packed to leave, and again when packed to come home.
    packed_going: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    packed_return: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # mine | ai | admin
    source: Mapped[str] = mapped_column(String(10), nullable=False, default="mine")
    # Set for items that come from an admin default; deleting the default
    # deletes these with it.
    default_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("packing_defaults.id", ondelete="CASCADE"), nullable=True, index=True,
    )
