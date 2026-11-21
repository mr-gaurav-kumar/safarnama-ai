"""Shared FastAPI dependencies: who is calling, and may they."""
import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import InvalidTokenError, decode_access_token
from app.models.user import User
from app.services import user_service

bearer_scheme = HTTPBearer(auto_error=False)

_CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise _CREDENTIALS_ERROR

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = uuid.UUID(payload["sub"])
    except (InvalidTokenError, KeyError, ValueError):
        raise _CREDENTIALS_ERROR from None

    user = user_service.get_by_id(db, user_id)
    if user is None:
        raise _CREDENTIALS_ERROR

    # Checked against the row, not the token: a user blocked after their token
    # was issued must lose access immediately.
    if user.is_blocked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Account is blocked"
        )

    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    """Every /admin route depends on this. The frontend guard is cosmetic;
    this is the check that matters.

    Three things, all from the database row: the admin role, a verified
    address, and that address being ADMIN_EMAIL. A role set by hand in the
    database, or an unverified sign-up using the admin's address, gets nothing.
    """
    if not (
        user.role == "admin"
        and user.is_verified
        and user_service.is_designated_admin_email(user.email)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )
    return user
