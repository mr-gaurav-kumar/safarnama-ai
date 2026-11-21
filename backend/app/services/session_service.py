"""Issuing, rotating and revoking refresh tokens.

    issue(db, user)           -> new family, returns the raw token for the cookie
    rotate(db, raw_token)     -> (user, new raw token) or raises RefreshRejected
    revoke_family(db, raw)    -> logout

Only the SHA-256 of a token is ever stored.
"""
from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.refresh_token import RefreshToken
from app.models.user import User


class RefreshRejected(Exception):
    """The cookie cannot be exchanged. `blocked` separates a blocked account
    (403) from a merely bad or expired token (401)."""

    def __init__(self, reason: str, *, blocked: bool = False) -> None:
        super().__init__(reason)
        self.blocked = blocked


def _hash(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: datetime) -> datetime:
    # SQLite returns naive datetimes; Postgres returns aware ones.
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _new_row(db: Session, user_id: uuid.UUID, family_id: uuid.UUID) -> str:
    raw = secrets.token_urlsafe(32)  # 256 bits
    db.add(RefreshToken(
        user_id=user_id,
        family_id=family_id,
        token_hash=_hash(raw),
        expires_at=_now() + timedelta(days=settings.REFRESH_TOKEN_DAYS),
    ))
    return raw


def issue(db: Session, user: User) -> str:
    """Start a new session family (on login or sign-up)."""
    raw = _new_row(db, user.id, uuid.uuid4())
    db.commit()
    return raw


def _revoke_family(db: Session, family_id: uuid.UUID, reason: str) -> None:
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=_now(), revoke_reason=reason)
    )
    db.commit()


def rotate(db: Session, raw: str | None) -> tuple[User, str]:
    """Exchange a refresh token for a new one. The presented token stops
    working (after a short grace, for tabs that refreshed at the same time)."""
    if not raw:
        raise RefreshRejected("missing")

    row = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == _hash(raw)))
    if row is None:
        raise RefreshRejected("unknown")

    now = _now()
    if row.revoked_at is not None:
        in_grace = (
            row.revoke_reason == "rotated"
            and now - _aware(row.revoked_at) <= timedelta(seconds=settings.REFRESH_REUSE_GRACE_SECONDS)
        )
        if not in_grace:
            # An old token came back. Either it was stolen or something is
            # badly wrong; end every session in this family.
            if row.revoke_reason == "rotated":
                _revoke_family(db, row.family_id, "reuse")
            raise RefreshRejected("revoked")

    if _aware(row.expires_at) <= now:
        raise RefreshRejected("expired")

    user = db.get(User, row.user_id)
    if user is None:
        raise RefreshRejected("unknown")
    if user.is_blocked:
        _revoke_family(db, row.family_id, "blocked")
        raise RefreshRejected("blocked", blocked=True)

    if row.revoked_at is None:
        row.revoked_at = now
        row.revoke_reason = "rotated"
    new_raw = _new_row(db, user.id, row.family_id)
    db.commit()
    return user, new_raw


def revoke(db: Session, raw: str | None) -> None:
    """Logout: end this session's whole family. Unknown tokens are ignored --
    logging out must always succeed."""
    if not raw:
        return
    row = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == _hash(raw)))
    if row is not None:
        _revoke_family(db, row.family_id, "logout")


def revoke_all_for_user(db: Session, user_id: uuid.UUID, reason: str = "blocked") -> None:
    """End every session a user has -- used when an admin blocks them."""
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=_now(), revoke_reason=reason)
    )
    db.commit()
