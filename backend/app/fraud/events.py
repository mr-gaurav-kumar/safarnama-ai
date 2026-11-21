"""Recording the activity the risk scorer looks at. Cheap: one insert, done in
the request. Scoring is a separate background job."""
from __future__ import annotations

import uuid

from fastapi import Request
from sqlalchemy.orm import Session

from app.models.risk import ActivityEvent

KINDS = ("signup", "login_ok", "login_failed", "trip_created", "invite_sent", "match_request")


def client_ip(request: Request | None) -> str | None:
    # Behind a reverse proxy, run uvicorn with --proxy-headers so this is the
    # real client address rather than the proxy's.
    return request.client.host if request is not None and request.client else None


def record(
    db: Session, kind: str, *, user_id: uuid.UUID | None, ip: str | None,
    trip_id: uuid.UUID | None = None,
) -> None:
    assert kind in KINDS, kind
    db.add(ActivityEvent(kind=kind, user_id=user_id, ip=ip, trip_id=trip_id))
    db.commit()
