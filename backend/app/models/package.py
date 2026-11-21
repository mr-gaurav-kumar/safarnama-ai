"""Travel packages the admin publishes, and travellers' bookings of them."""
import uuid
from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, Integer, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.trip import JSONColumn


class TravelPackage(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "travel_packages"

    title: Mapped[str] = mapped_column(String(160), nullable=False)
    destination: Mapped[str] = mapped_column(String(200), nullable=False)
    duration_days: Mapped[int] = mapped_column(Integer, nullable=False)
    price_per_person: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    summary: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # Short lists shown as bullets: what is included, and the day-wise outline.
    inclusions: Mapped[list[str]] = mapped_column(JSONColumn, default=list, nullable=False)
    highlights: Mapped[list[str]] = mapped_column(JSONColumn, default=list, nullable=False)
    style_tags: Mapped[list[str]] = mapped_column(JSONColumn, default=list, nullable=False)
    # Photo URLs, cover first: "/media/packages/<file>" for uploads, or an
    # https:// link the admin pasted.
    images: Mapped[list[str]] = mapped_column(JSONColumn, default=list, nullable=False)
    # Total seats across all departures; null means no limit.
    seats: Mapped[int | None] = mapped_column(Integer, nullable=True)
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Null for the platform's own packages; a business account's id otherwise.
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=True,
    )

    bookings: Mapped[list["PackageBooking"]] = relationship(
        back_populates="package", cascade="all, delete-orphan",
    )


class PackageBooking(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "package_bookings"

    package_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("travel_packages.id", ondelete="CASCADE"), index=True, nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False,
    )
    travelers: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    total_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # pending -> confirmed | cancelled
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)

    package: Mapped[TravelPackage] = relationship(back_populates="bookings")
