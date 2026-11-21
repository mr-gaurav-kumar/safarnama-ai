"""Everything the chatbot knows when it answers: this user's own trips, any
that look stuck, the past trips most like what they are asking about (the same
pgvector memory the planner uses), and the recent conversation.

Only ever this user's data -- the bot never sees anyone else's.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.chat import ChatMessage
from app.models.trip import Trip
from app.models.user import User
from app.rag import retrieval

RECENT_TRIPS = 5
HISTORY_MESSAGES = 8


@dataclass
class TripFact:
    id: str
    destination: str
    start: date
    end: date
    status: str
    minutes_since_created: int

    @property
    def upcoming(self) -> bool:
        return self.start >= date.today()


@dataclass
class ChatContext:
    user_name: str
    email: str
    email_verified: bool
    trips: list[TripFact] = field(default_factory=list)
    stuck: list[TripFact] = field(default_factory=list)
    failed: list[TripFact] = field(default_factory=list)
    memory: list[retrieval.MemoryHit] = field(default_factory=list)
    history: list[tuple[str, str]] = field(default_factory=list)  # (sender, message)


def _aware(dt: datetime) -> datetime:
    # SQLite hands back naive datetimes; Postgres hands back aware ones.
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def build_context(db: Session, user: User, message: str) -> ChatContext:
    now = datetime.now(timezone.utc)
    rows = db.scalars(
        select(Trip).where(Trip.user_id == user.id)
        .order_by(Trip.created_at.desc()).limit(RECENT_TRIPS)
    ).all()
    trips = [
        TripFact(
            id=str(t.id), destination=t.destination, start=t.start_date, end=t.end_date,
            status=t.status,
            minutes_since_created=int((now - _aware(t.created_at)).total_seconds() // 60),
        )
        for t in rows
    ]
    stuck_after = settings.STUCK_TRIP_MINUTES

    ctx = ChatContext(
        user_name=user.name,
        email=user.email,
        email_verified=user.is_verified,
        trips=trips,
        stuck=[t for t in trips if t.status == "processing" and t.minutes_since_created >= stuck_after],
        failed=[t for t in trips if t.status == "failed"],
    )

    # The same memory the planner uses: which past trips is this about?
    ctx.memory = retrieval.find_similar_trips(
        db, user_id=user.id, query_text=message, top_k=2,
    )

    recent = db.scalars(
        select(ChatMessage).where(ChatMessage.user_id == user.id)
        .order_by(ChatMessage.created_at.desc()).limit(HISTORY_MESSAGES)
    ).all()
    ctx.history = [(m.sender, m.message) for m in reversed(recent)]
    return ctx


def describe_for_llm(ctx: ChatContext) -> str:
    """The context as compact lines for the model's prompt."""
    lines = [f"User: {ctx.user_name}. Email {'verified' if ctx.email_verified else 'NOT verified'}."]
    if ctx.trips:
        lines.append("Their recent trips (newest first):")
        for t in ctx.trips:
            lines.append(
                f"- {t.destination}, {t.start:%d %b %Y} to {t.end:%d %b %Y}, status {t.status}"
                + (" (STUCK: planning for over "
                   f"{t.minutes_since_created} min)" if t in ctx.stuck else "")
            )
    else:
        lines.append("They have not planned any trips yet.")
    if ctx.memory:
        lines.append("Past trips most related to this message: "
                     + " | ".join(h.source_text for h in ctx.memory))
    return "\n".join(lines)


def since(minutes: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(minutes=minutes)
