"""WebSocket authentication, shared by every socket.

Browsers cannot put headers on a WebSocket, and a token in the URL ends up in
server and proxy logs -- so the client sends it as the first message:

    {"type": "auth", "token": "<access token>"}
"""
from __future__ import annotations

import asyncio
import uuid

from fastapi import WebSocket

from app.core.security import InvalidTokenError, decode_access_token

AUTH_TIMEOUT_SECONDS = 10
CLOSE_UNAUTHORISED = 4401
CLOSE_NOT_FOUND = 4404
CLOSE_RATE_LIMITED = 4429


async def authenticate(websocket: WebSocket) -> uuid.UUID | None:
    try:
        message = await asyncio.wait_for(websocket.receive_json(), timeout=AUTH_TIMEOUT_SECONDS)
        if message.get("type") != "auth":
            return None
        claims = decode_access_token(str(message.get("token", "")))
        return uuid.UUID(claims["sub"])
    except (asyncio.TimeoutError, InvalidTokenError, KeyError, ValueError, TypeError):
        return None
