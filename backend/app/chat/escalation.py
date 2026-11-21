"""When the bot should hand a conversation to a person (§4.9).

  * negative sentiment -- someone is upset; a template will not fix that
  * a repeated issue   -- the same problem raised REPEAT_THRESHOLD times inside
                          REPEAT_WINDOW_MINUTES, so the bot is not solving it

One open escalation per person at a time: while one raised in the last
DEDUPE_MINUTES is still open, further triggers join it rather than flooding
the team with duplicates.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.chat.classify import ACTIONABLE
from app.chat.context import since
from app.models.chat import ChatMessage, SupportEscalation

REPEAT_THRESHOLD = 3
REPEAT_WINDOW_MINUTES = 15
DEDUPE_MINUTES = 30


@dataclass(frozen=True)
class Decision:
    escalate: bool
    reason: str | None = None
    already_open: SupportEscalation | None = None


def decide(db: Session, *, user_id: uuid.UUID, intent: str, sentiment: str) -> Decision:
    """Call after the user's message has been saved."""
    reason = None
    if sentiment == "negative":
        reason = "negative_sentiment"
    elif intent in ACTIONABLE:
        same = db.scalar(
            select(func.count()).select_from(ChatMessage).where(
                ChatMessage.user_id == user_id,
                ChatMessage.sender == "user",
                ChatMessage.intent == intent,
                ChatMessage.created_at >= since(REPEAT_WINDOW_MINUTES),
            )
        ) or 0
        if same >= REPEAT_THRESHOLD:
            reason = "repeated_issue"

    if reason is None:
        return Decision(escalate=False)

    open_one = db.scalar(
        select(SupportEscalation).where(
            SupportEscalation.user_id == user_id,
            SupportEscalation.status == "open",
            SupportEscalation.created_at >= since(DEDUPE_MINUTES),
        ).order_by(SupportEscalation.created_at.desc())
    )
    return Decision(escalate=True, reason=reason, already_open=open_one)


def open_escalation(
    db: Session, *, user_id: uuid.UUID, reason: str, intent: str, excerpt: str
) -> SupportEscalation:
    row = SupportEscalation(
        user_id=user_id, reason=reason, intent=intent, excerpt=excerpt[:500], status="open",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
