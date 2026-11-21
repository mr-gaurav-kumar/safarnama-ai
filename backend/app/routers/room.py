"""WS /ws/trips/{trip_id}/room -- the group's live discussion (§4.10).

Protocol
  client -> {"type": "auth", "token": "..."}
  server -> {"type": "history", "messages": [...]}          last 50, oldest first
  client -> {"type": "message", "text": "..."}
  server -> {"type": "message", "message": {...}}            to everyone in the room
  server -> {"type": "members_changed"}                      someone joined/left/changed tags
  server -> {"type": "error", "code": ..., "detail": ...}

Messages are saved, then fanned out through the same broker as trip progress:
in-process for TASK_BACKEND=inline, Redis pub/sub for celery -- so two API
processes still share one room. Membership is re-checked on every message, so
someone removed from the trip stops being able to post at once.
"""
from __future__ import annotations

import asyncio
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from starlette.concurrency import run_in_threadpool

from app.core import database, ratelimit
from app.core.config import settings
from app.models.group import TripRoomMessage
from app.models.trip import Trip
from app.models.user import User
from app.realtime.progress import get_broker
from app.realtime.ws_auth import CLOSE_NOT_FOUND, CLOSE_UNAUTHORISED, authenticate
from app.services.group_service import role_on

router = APIRouter(tags=["group"])

HISTORY = 50
ROOM_MESSAGES_PER_MINUTE = 20


def channel(trip_id: uuid.UUID) -> str:
    return f"trip:{trip_id}:room"


def _out(m: TripRoomMessage, name: str) -> dict:
    return {
        "id": str(m.id), "user_id": str(m.user_id), "name": name,
        "text": m.message, "created_at": m.created_at.isoformat(),
    }


def _can_enter(user_id: uuid.UUID, trip_id: uuid.UUID) -> bool:
    with database.SessionLocal() as db:
        user = db.get(User, user_id)
        trip = db.get(Trip, trip_id)
        return bool(user and not user.is_blocked and trip and role_on(db, user_id, trip))


def _history(trip_id: uuid.UUID) -> list[dict]:
    with database.SessionLocal() as db:
        rows = db.execute(
            select(TripRoomMessage, User.name).join(User, User.id == TripRoomMessage.user_id)
            .where(TripRoomMessage.trip_id == trip_id)
            .order_by(TripRoomMessage.created_at.desc()).limit(HISTORY)
        ).all()
        return [_out(m, name) for m, name in reversed(rows)]


def _post(user_id: uuid.UUID, trip_id: uuid.UUID, text: str) -> dict | None:
    with database.SessionLocal() as db:
        user = db.get(User, user_id)
        trip = db.get(Trip, trip_id)
        if not (user and not user.is_blocked and trip and role_on(db, user_id, trip)):
            return None
        row = TripRoomMessage(trip_id=trip_id, user_id=user_id, message=text)
        db.add(row)
        db.commit()
        db.refresh(row)
        return _out(row, user.name)


@router.websocket("/ws/trips/{trip_id}/room")
async def trip_room(websocket: WebSocket, trip_id: uuid.UUID) -> None:
    await websocket.accept()
    user_id = await authenticate(websocket)
    if user_id is None:
        await websocket.close(code=CLOSE_UNAUTHORISED)
        return
    if not await run_in_threadpool(_can_enter, user_id, trip_id):
        await websocket.close(code=CLOSE_NOT_FOUND)
        return

    try:
        # Subscribe before reading history, so nothing posted in between is
        # lost; ids already sent are skipped when they arrive live.
        async with get_broker().subscribe(channel(trip_id)) as (_backlog, queue):
            history = await run_in_threadpool(_history, trip_id)
            sent = {m["id"] for m in history}
            await websocket.send_json({"type": "history", "messages": history})

            incoming = asyncio.create_task(websocket.receive_json())
            outgoing = asyncio.create_task(queue.get())
            try:
                while True:
                    done, _ = await asyncio.wait({incoming, outgoing}, return_when=asyncio.FIRST_COMPLETED)

                    if outgoing in done:
                        event = outgoing.result()
                        outgoing = asyncio.create_task(queue.get())
                        if event.get("type") == "message":
                            mid = event["message"]["id"]
                            if mid in sent:
                                continue
                            sent.add(mid)
                        await websocket.send_json({k: v for k, v in event.items() if k != "seq"})

                    if incoming in done:
                        data = incoming.result()
                        incoming = asyncio.create_task(websocket.receive_json())
                        if await _handle(websocket, user_id, trip_id, data) is False:
                            return
            finally:
                incoming.cancel()
                outgoing.cancel()
    except WebSocketDisconnect:
        return


async def _handle(websocket: WebSocket, user_id: uuid.UUID, trip_id: uuid.UUID, data: dict) -> bool:
    if data.get("type") != "message":
        return True
    text = str(data.get("text", "")).strip()
    if not text:
        return True
    if len(text) > settings.CHAT_MAX_CHARS:
        await websocket.send_json({"type": "error", "code": "too_long",
                                   "detail": f"At most {settings.CHAT_MAX_CHARS} characters."})
        return True
    allowed, retry = ratelimit.check("room", str(user_id), limit=ROOM_MESSAGES_PER_MINUTE, window_seconds=60)
    if not allowed:
        await websocket.send_json({"type": "error", "code": "rate_limited",
                                   "detail": f"Slow down -- try again in {retry}s."})
        return True

    message = await run_in_threadpool(_post, user_id, trip_id, text)
    if message is None:  # removed from the trip mid-conversation
        await websocket.close(code=CLOSE_NOT_FOUND)
        return False
    get_broker().publish(channel(trip_id), {"type": "message", "message": message})
    return True
