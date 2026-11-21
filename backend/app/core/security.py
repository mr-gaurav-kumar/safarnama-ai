"""Password hashing and JWT creation/verification.

bcrypt is used directly rather than through passlib: passlib is unmaintained and
its bcrypt backend breaks against bcrypt 4.x. This is the only module that knows
how a password becomes a hash or how a token is signed.
"""
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings

# bcrypt silently truncates anything past 72 bytes, which would make two
# different long passwords interchangeable. Reject instead.
MAX_PASSWORD_BYTES = 72


class InvalidTokenError(Exception):
    """Raised when a token is missing, malformed, expired, wrongly signed, or
    of the wrong type."""


# Every token says what it is for. Without this, the verification link in a
# sign-up email -- a signed token carrying the user's id -- would also work as
# a 24-hour login token for whoever reads that email.
ACCESS_TOKEN = "access"
EMAIL_VERIFY_TOKEN = "verify_email"
PASSWORD_RESET_TOKEN = "reset_password"


def hash_password(password: str) -> str:
    raw = password.encode("utf-8")
    if len(raw) > MAX_PASSWORD_BYTES:
        raise ValueError(f"Password must be at most {MAX_PASSWORD_BYTES} bytes")
    return bcrypt.hashpw(raw, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    raw = password.encode("utf-8")
    if len(raw) > MAX_PASSWORD_BYTES:
        return False
    try:
        return bcrypt.checkpw(raw, password_hash.encode("utf-8"))
    except ValueError:
        # Stored hash is not a valid bcrypt hash -- treat as a failed login,
        # never as a crash.
        return False


def _encode(payload: dict[str, Any], lifetime: timedelta) -> str:
    now = datetime.now(timezone.utc)
    claims = {
        **payload,
        "iat": int(now.timestamp()),
        "exp": int((now + lifetime).timestamp()),
    }
    return jwt.encode(claims, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def _decode(token: str, expected_type: str) -> dict[str, Any]:
    try:
        claims = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
    except JWTError as exc:
        raise InvalidTokenError(str(exc)) from exc
    if claims.get("typ") != expected_type:
        raise InvalidTokenError(f"Expected a {expected_type} token")
    return claims


def create_access_token(subject: str, role: str) -> str:
    """`subject` is the user's id. Role is carried so routes can check it
    without a database round trip -- the row is still the source of truth."""
    return _encode(
        {"sub": subject, "role": role, "typ": ACCESS_TOKEN},
        timedelta(minutes=settings.JWT_EXPIRE_MINUTES),
    )


def decode_access_token(token: str) -> dict[str, Any]:
    return _decode(token, ACCESS_TOKEN)


def create_email_verification_token(user_id: str, email: str) -> str:
    """The email is included so that changing the address on the account
    invalidates any link sent to the old one."""
    return _encode(
        {"sub": user_id, "email": email, "typ": EMAIL_VERIFY_TOKEN},
        timedelta(hours=settings.EMAIL_VERIFY_EXPIRE_HOURS),
    )


def decode_email_verification_token(token: str) -> dict[str, Any]:
    return _decode(token, EMAIL_VERIFY_TOKEN)


# --- password reset ------------------------------------------------------------

def password_fingerprint(password_hash: str) -> str:
    """A short digest of the current password hash. Put in the reset token, it
    makes the link single-use: once the password changes, the fingerprint no
    longer matches and every earlier link stops working."""
    return hashlib.sha256(password_hash.encode("utf-8")).hexdigest()[:16]


def create_password_reset_token(user_id: str, password_hash: str) -> str:
    return _encode(
        {"sub": user_id, "pwf": password_fingerprint(password_hash), "typ": PASSWORD_RESET_TOKEN},
        timedelta(minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES),
    )


def decode_password_reset_token(token: str) -> dict[str, Any]:
    return _decode(token, PASSWORD_RESET_TOKEN)
