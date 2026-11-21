"""Destination features for the budget recommender and the season model
(Phase 8). Seeded from the curated list in app/data/destinations.py."""
from typing import Any

from sqlalchemy import JSON, Boolean, Float, Integer, String
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin

JSONColumn = JSON().with_variant(postgresql.JSONB, "postgresql")


class DestinationFeature(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "destination_features"

    name: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    state: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    region: Mapped[str] = mapped_column(String(40), nullable=False)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)
    altitude_m: Mapped[int] = mapped_column(Integer, nullable=False)
    coastal: Mapped[bool] = mapped_column(Boolean, nullable=False)
    # Typical mid-range on-ground spend per person per day, INR.
    daily_cost: Mapped[int] = mapped_column(Integer, nullable=False)
    # {"adventure": 0-1, "relax": ..., "culture": ..., "food": ..., "nature": ...}
    styles: Mapped[dict[str, Any]] = mapped_column(JSONColumn, nullable=False)
    blurb: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    aliases: Mapped[list[str]] = mapped_column(JSONColumn, nullable=False, default=list)
    closed_months: Mapped[list[int]] = mapped_column(JSONColumn, nullable=False, default=list)
    # "curated" for the hand-made seed rows; anything else names a real source.
    source: Mapped[str] = mapped_column(String(40), nullable=False, default="curated")

    def __repr__(self) -> str:
        return f"<DestinationFeature {self.name}>"
