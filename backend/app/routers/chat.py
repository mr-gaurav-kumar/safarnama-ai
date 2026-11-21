"""Support chat -- WS /ws/chat for the widget, GET /chat/history for a reload.

Protocol
  client -> {"type": "auth", "token": "..."}                   first, within 10 s
  server -> {"type": "history", "messages": [...]}
  client -> {"type": "message", "text": "..."}
  server -> {"type": "typing"}
  server -> {"type": "reply", "message": {...}, "escalated": bool}
  server -> {"type": "error", "code": "rate_limited" | "too_long" | "empty", ...}

Every message is checked against a per-user limit before anything else runs, so
a stuck client cannot run up the LLM bill.
"""
from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.chat import pages
from app.chat import service
from app.core import database, ratelimit
from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.chat import ChatMessage
from app.models.user import User
from app.realtime.ws_auth import CLOSE_UNAUTHORISED, authenticate
from app.tasks import jobs
from app.tasks.dispatch import enqueue

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])


class ChatMessageOut(BaseModel):
    id: str
    sender: str
    message: str
    created_at: str


def _out(m: ChatMessage) -> dict:
    return ChatMessageOut(
        id=str(m.id), sender=m.sender, message=m.message, created_at=m.created_at.isoformat()
    ).model_dump()


@router.get("/chat/help/{page}")
def chat_help(page: str) -> dict:
    """What the Help chat says when it opens on a page: title, first line and
    the questions to offer. Public -- it is the same for everyone."""
    p = pages.page_for(page)
    return {"page": page if page in pages.PAGES else None, "title": p.title, "intro": p.intro, "starters": p.starters}


class PublicQuestion(BaseModel):
    message: str = Field(min_length=1, max_length=500)
    page: str | None = Field(default=None, max_length=40)


@router.post("/chat/public")
def public_help(payload: PublicQuestion, request: Request) -> dict:
    """Help for people who aren't logged in (login, sign-up, the landing page).
    Answers only from the help notes: no account data, no model call, nothing
    saved -- and limited per IP, as anyone can call it."""
    from app.fraud.events import client_ip

    allowed, retry_after = ratelimit.check(
        "chat-public", client_ip(request) or "unknown", limit=settings.CHAT_MESSAGES_PER_MINUTE, window_seconds=60,
    )
    if not allowed:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                            detail=f"You're asking quickly — try again in {retry_after}s.")
    page = payload.page if payload.page in pages.PAGES else None
    return {"reply": pages.public_reply(page, payload.message.strip())}


@router.get("/chat/history", response_model=list[ChatMessageOut])
def chat_history(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict]:
    return [_out(m) for m in service.history(db, user)]


# --- the socket -------------------------------------------------------------

def _active_user(user_id: uuid.UUID) -> User | None:
    with database.SessionLocal() as db:
        user = db.get(User, user_id)
        if user is None or user.is_blocked:
            return None
        db.expunge(user)
        return user


def _history(user_id: uuid.UUID) -> list[dict]:
    with database.SessionLocal() as db:
        user = db.get(User, user_id)
        return [_out(m) for m in service.history(db, user)] if user else []


def _answer(user_id: uuid.UUID, text: str, page: str | None = None) -> tuple[dict, service.Turn] | None:
    with database.SessionLocal() as db:
        user = db.get(User, user_id)
        if user is None or user.is_blocked:
            return None
        turn = service.handle_message(db, user, text, page)
        last_bot = service.history(db, user, limit=1)[-1]
        return _out(last_bot), turn


@router.websocket("/ws/chat")
async def chat_socket(websocket: WebSocket) -> None:
    await websocket.accept()

    user_id = await authenticate(websocket)
    if user_id is None or await run_in_threadpool(_active_user, user_id) is None:
        await websocket.close(code=CLOSE_UNAUTHORISED)
        return

    try:
        await websocket.send_json(
            {"type": "history", "messages": await run_in_threadpool(_history, user_id)}
        )
        while True:
            incoming = await websocket.receive_json()
            if incoming.get("type") != "message":
                continue

            text = str(incoming.get("text", "")).strip()
            if not text:
                await websocket.send_json({"type": "error", "code": "empty"})
                continue
            if len(text) > settings.CHAT_MAX_CHARS:
                await websocket.send_json({
                    "type": "error", "code": "too_long",
                    "detail": f"Messages can be at most {settings.CHAT_MAX_CHARS} characters.",
                })
                continue

            allowed, retry_after = ratelimit.check(
                "chat", str(user_id),
                limit=settings.CHAT_MESSAGES_PER_MINUTE, window_seconds=60,
            )
            if not allowed:
                await websocket.send_json({
                    "type": "error", "code": "rate_limited", "retry_after": retry_after,
                    "detail": f"You're sending messages quickly -- try again in {retry_after}s.",
                })
                continue

            await websocket.send_json({"type": "typing"})
            # Which page they are asking from -- only a page we know.
            page = incoming.get("page") if incoming.get("page") in pages.PAGES else None
            result = await run_in_threadpool(_answer, user_id, text, page)
            if result is None:  # blocked mid-conversation
                await websocket.close(code=CLOSE_UNAUTHORISED)
                return
            message, turn = result
            await websocket.send_json(
                {"type": "reply", "message": message, "escalated": turn.escalated}
            )

            # After the reply, so the person is never kept waiting on an email.
            if turn.new_escalation and turn.escalation_id:
                await run_in_threadpool(
                    enqueue, None, jobs.send_escalation_alert, turn.escalation_id
                )
    except WebSocketDisconnect:
        return
