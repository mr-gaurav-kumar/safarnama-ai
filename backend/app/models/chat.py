"""Support chat -- §5.1 chat_logs, plus the escalations the chatbot raises."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class ChatMessage(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "chat_logs"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        index=True, nullable=False,
    )
    sender: Mapped[str] = mapped_column(String(10), nullable=False)  # 'user' | 'bot'
    message: Mapped[str] = mapped_column(Text, nullable=False)

    # Set on the user's messages; the bot's carry the intent they answered.
    intent: Mapped[str | None] = mapped_column(String(40), nullable=True)
    sentiment: Mapped[str | None] = mapped_column(String(10), nullable=True)


class SupportEscalation(UUIDMixin, TimestampMixin, Base):
    """A conversation the chatbot handed to a person. The admin dashboard
    (Phase 7) lists these; until then the admin is emailed."""

    __tablename__ = "support_escalations"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        index=True, nullable=False,
    )
    # 'negative_sentiment' | 'repeated_issue'
    reason: Mapped[str] = mapped_column(String(30), nullable=False)
    intent: Mapped[str | None] = mapped_column(String(40), nullable=True)
    # The message that tipped it over, so whoever picks it up has the gist.
    excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(12), default="open", nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
