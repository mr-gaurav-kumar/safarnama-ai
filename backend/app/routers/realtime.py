"""WS /ws/trips/{trip_id} -- live progress while an itinerary is generated.

Protocol
  client -> {"type": "auth", "token": "<access token>"}      first message, within 10 s
  server -> {"type": "status", "status": "processing"}        current state from the DB
  server -> {"type": "progress", "step": ..., "message": ..., "seq": n}   ...
  server -> {"type": "done", "status": "completed"|"failed", "error": ...}
  server closes.

The token goes in the first message, not the URL: browsers cannot set headers
on a WebSocket, and a token in a query string ends up in proxy and server logs.

Because the server always sends the database state first, a client that
reconnects after a dropped connection -- or opens the page after generation
already finished -- is never left waiting on events it missed.

Close codes: 4401 not authenticated, 4404 no such trip for this user.
"""
from __future__ import annotations

import asyncio
import logging
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.concurrency import run_in_threadpool

from app.core import database
from app.models.trip import Trip
from app.models.user import User
from app.realtime.progress import channel_for, get_broker
from app.realtime.ws_auth import CLOSE_NOT_FOUND, CLOSE_UNAUTHORISED, authenticate
from app.services.group_service import role_on

logger = logging.getLogger(__name__)

router = APIRouter(tags=["realtime"])

# How long to wait on the broker before checking the database directly. Covers
# a worker that died without publishing "done".
RECHECK_SECONDS = 15
# Give up after this long; the page falls back to polling.
MAX_WATCH_SECONDS = 300



def _load_status(user_id: uuid.UUID, trip_id: uuid.UUID) -> tuple[str, str | None] | None:
    """(status, error) for a trip this user owns, or None. Blocking -- run it
    in the thread pool."""
    with database.SessionLocal() as db:
        user = db.get(User, user_id)
        if user is None or user.is_blocked:
            return None
        trip = db.get(Trip, trip_id)
        if trip is None or role_on(db, user_id, trip) is None:
            return None
        return trip.status, trip.error


@router.websocket("/ws/trips/{trip_id}")
async def trip_progress(websocket: WebSocket, trip_id: uuid.UUID) -> None:
    await websocket.accept()

    user_id = await authenticate(websocket)
    if user_id is None:
        await websocket.close(code=CLOSE_UNAUTHORISED)
        return

    state = await run_in_threadpool(_load_status, user_id, trip_id)
    if state is None:
        # Same answer for "does not exist" and "not yours".
        await websocket.close(code=CLOSE_NOT_FOUND)
        return

    try:
        await _stream(websocket, user_id, trip_id, state)
    except WebSocketDisconnect:
        return  # the browser went away; nothing to clean up beyond the broker


async def _stream(
    websocket: WebSocket,
    user_id: uuid.UUID,
    trip_id: uuid.UUID,
    state: tuple[str, str | None],
) -> None:
    status, error = state
    await websocket.send_json({"type": "status", "status": status})

    if status != "processing":
        await _finish(websocket, status, error)
        return

    async with get_broker().subscribe(channel_for(trip_id)) as (backlog, queue):
        last_seq = 0

        async def forward(event: dict) -> bool:
            """Send one event; True once the job has finished."""
            nonlocal last_seq
            if event.get("seq", 0) <= last_seq:
                return False  # already sent -- arrived via both backlog and live
            last_seq = event["seq"]
            await websocket.send_json(event)
            return event.get("type") == "done"

        for event in backlog:
            if await forward(event):
                await websocket.close()
                return

        # The job may have finished between the first status read and the
        # subscription, with "done" published before we were listening.
        state = await run_in_threadpool(_load_status, user_id, trip_id)
        if state is None:
            await websocket.close(code=CLOSE_NOT_FOUND)
            return
        if state[0] != "processing":
            await _finish(websocket, *state)
            return

        loop = asyncio.get_running_loop()
        deadline = loop.time() + MAX_WATCH_SECONDS
        while loop.time() < deadline:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=RECHECK_SECONDS)
            except asyncio.TimeoutError:
                state = await run_in_threadpool(_load_status, user_id, trip_id)
                if state is None or state[0] != "processing":
                    await _finish(websocket, *(state or ("failed", None)))
                    return
                continue
            if await forward(event):
                await websocket.close()
                return

        await websocket.close()


async def _finish(websocket: WebSocket, status: str, error: str | None) -> None:
    await websocket.send_json({"type": "done", "status": status, "error": error})
    await websocket.close()
