"""One turn of support chat: save, classify, decide, answer, save."""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.chat import escalation
from app.chat.context import build_context
from app.chat.reply import draft_reply
from app.models.chat import ChatMessage
from app.models.user import User

HANDOFF = (" I've passed this to our support team, and someone will follow up by "
           "email{where}.")
ALREADY = (" Our support team already has your conversation and will follow up "
           "by email{where}.")


@dataclass
class Turn:
    reply: str
    intent: str
    sentiment: str
    escalated: bool
    escalation_id: str | None
    new_escalation: bool


def handle_message(db: Session, user: User, text: str, page: str | None = None) -> Turn:
    ctx = build_context(db, user, text)
    draft = draft_reply(text, ctx, page)

    db.add(ChatMessage(
        user_id=user.id, sender="user", message=text,
        intent=draft.intent, sentiment=draft.sentiment,
    ))
    db.commit()

    decision = escalation.decide(
        db, user_id=user.id, intent=draft.intent, sentiment=draft.sentiment
    )
    reply = draft.reply
    escalation_id = None
    new = False
    if decision.escalate:
        where = f" at {user.email}" if user.is_verified else ""
        # A vague complaint gets an apology and a person -- not a menu of
        # things the bot can do, which reads as not listening.
        if draft.intent == "other" and not draft.from_model:
            reply = "Sorry about the trouble."
        if decision.already_open is not None:
            escalation_id = str(decision.already_open.id)
            reply += ALREADY.format(where=where)
        else:
            row = escalation.open_escalation(
                db, user_id=user.id, reason=decision.reason or "negative_sentiment",
                intent=draft.intent, excerpt=text,
            )
            escalation_id = str(row.id)
            new = True
            reply += HANDOFF.format(where=where)

    db.add(ChatMessage(user_id=user.id, sender="bot", message=reply, intent=draft.intent))
    db.commit()

    return Turn(
        reply=reply, intent=draft.intent, sentiment=draft.sentiment,
        escalated=decision.escalate, escalation_id=escalation_id, new_escalation=new,
    )


def history(db: Session, user: User, limit: int = 30) -> list[ChatMessage]:
    rows = db.scalars(
        select(ChatMessage).where(ChatMessage.user_id == user.id)
        .order_by(ChatMessage.created_at.desc()).limit(limit)
    ).all()
    return list(reversed(rows))
