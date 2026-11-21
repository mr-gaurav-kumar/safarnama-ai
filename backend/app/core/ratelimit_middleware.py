"""Rate limiting for every HTTP endpoint (§4.13).

Plain ASGI rather than BaseHTTPMiddleware, so it adds nothing to requests it
lets through and never interferes with background tasks or WebSockets
(WebSocket messages are limited in their own handlers).

Who is limited: the user named in a valid access token, otherwise the client
IP. Login and sign-up are always per IP -- there is no user yet, and that is
exactly where password guessing and account farming happen.
"""
from __future__ import annotations

import json

from starlette.types import ASGIApp, Receive, Scope, Send

from app.core import ratelimit
from app.core.config import settings
from app.core.security import InvalidTokenError, decode_access_token

EXEMPT = {"/health", "/health/db", "/", "/docs", "/openapi.json", "/redoc"}
AUTH_PATHS = {
    "/auth/login", "/auth/google", "/auth/signup", "/auth/signup-business", "/auth/verify", "/auth/resend-verification",
    "/auth/forgot-password", "/auth/reset-password", "/auth/change-password",
}
TRIP_CREATE = ("/trips",)


def _bucket(method: str, path: str) -> tuple[str, int, bool]:
    """(name, per-minute limit, always per IP)."""
    if method == "POST" and path in AUTH_PATHS:
        return "auth", settings.RATE_LIMIT_AUTH_PER_MIN, True
    if method == "POST" and path == "/auth/refresh":
        return "refresh", settings.RATE_LIMIT_REFRESH_PER_MIN, True
    if method == "POST" and path == "/assistant/chat":
        return "assistant", settings.RATE_LIMIT_ASSISTANT_PER_MIN, False
    if method == "POST" and (path in TRIP_CREATE or path.endswith("/replan")):
        return "trips", settings.RATE_LIMIT_TRIPS_PER_MIN, False
    if method in ("POST", "PUT", "PATCH", "DELETE"):
        return "writes", settings.RATE_LIMIT_WRITES_PER_MIN, False
    return "reads", settings.RATE_LIMIT_READS_PER_MIN, False


def _user_from(scope: Scope) -> str | None:
    for name, value in scope.get("headers", []):
        if name == b"authorization":
            raw = value.decode("latin-1")
            if raw.lower().startswith("bearer "):
                try:
                    return "u:" + decode_access_token(raw[7:])["sub"]
                except (InvalidTokenError, KeyError):
                    return None
    return None


class RateLimitMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if (
            scope["type"] != "http"
            or not settings.RATE_LIMIT_ENABLED
            or scope["method"] == "OPTIONS"
            or scope["path"] in EXEMPT
        ):
            await self.app(scope, receive, send)
            return

        bucket, limit, per_ip = _bucket(scope["method"], scope["path"])
        client = scope.get("client")
        ip = "ip:" + (client[0] if client else "unknown")
        who = ip if per_ip else (_user_from(scope) or ip)

        allowed, retry_after = ratelimit.check(bucket, who, limit=limit, window_seconds=60)
        if allowed:
            await self.app(scope, receive, send)
            return

        body = json.dumps({
            "detail": f"Too many requests -- please wait {retry_after}s and try again.",
            "retry_after": retry_after,
        }).encode()
        await send({
            "type": "http.response.start",
            "status": 429,
            "headers": [
                (b"content-type", b"application/json"),
                (b"retry-after", str(retry_after).encode()),
                (b"content-length", str(len(body)).encode()),
            ],
        })
        await send({"type": "http.response.body", "body": body})
