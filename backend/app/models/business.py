"""Travel agencies and businesses that publish packages on the platform."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class BusinessProfile(TimestampMixin, Base):
    """One per business account (users.role == 'business')."""

    __tablename__ = "business_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True,
    )
    business_name: Mapped[str] = mapped_column(String(160), nullable=False)
    # URL-safe handle for the public page: /b/<slug>
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    # agency | tour_operator | hotel | other
    kind: Mapped[str] = mapped_column(String(20), nullable=False, default="agency")
    city: Mapped[str] = mapped_column(String(120), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    website: Mapped[str | None] = mapped_column(String(200), nullable=True)
    gst_number: Mapped[str | None] = mapped_column(String(15), nullable=True)
    # pending -> approved | rejected; approved <-> suspended
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    status_reason: Mapped[str | None] = mapped_column(String(300), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
