"""Refresh tokens -- one row per issued token, stored only as a hash.

Tokens come in families: logging in starts a family, and every refresh
replaces the family's current token with a new one. If an old, already
replaced token is ever presented again (after a short grace for racing tabs),
someone has a copy they should not have, and the whole family is revoked.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class RefreshToken(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "refresh_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        index=True, nullable=False,
    )
    family_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), index=True, nullable=False)

    # SHA-256 of the token. The token itself is 256 random bits, so a fast hash
    # is enough -- nothing here can be brute-forced -- and a leaked table
    # contains nothing usable.
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)

    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # 'rotated' | 'logout' | 'reuse' | 'blocked'
    revoke_reason: Mapped[str | None] = mapped_column(String(12), nullable=True)
