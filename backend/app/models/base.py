"""Declarative base plus the columns every table shares."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Uuid, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class UUIDMixin:
    # sqlalchemy.Uuid maps to Postgres' native UUID in production and to a
    # portable type elsewhere, so the test suite can run without Postgres.
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    # Both a Python default and a server default: the server default keeps rows
    # inserted outside the ORM honest, while the Python one gives microsecond
    # precision. SQLite's CURRENT_TIMESTAMP is only accurate to the second, so
    # without this two rows created in the same second cannot be ordered.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        onupdate=_utcnow,
        server_default=func.now(),
        nullable=False,
    )
