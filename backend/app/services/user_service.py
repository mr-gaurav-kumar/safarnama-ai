"""Everything that reads or writes the users table.

Routers stay thin: they validate input, call one of these, and shape a response.
Business rules live here, so they are reusable from Celery tasks and testable
without HTTP.
"""
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import User


class EmailAlreadyRegistered(Exception):
    pass


class InvalidCredentials(Exception):
    """Raised for a wrong email AND a wrong password -- the caller must not be
    able to tell which, or the endpoint becomes an account-enumeration oracle."""


class AccountBlocked(Exception):
    pass


def get_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email.lower()))


def get_by_id(db: Session, user_id: uuid.UUID) -> User | None:
    return db.get(User, user_id)


def create_user(db: Session, *, name: str, email: str, password: str, **profile) -> User:
    email = email.lower()
    if get_by_email(db, email) is not None:
        raise EmailAlreadyRegistered(email)

    user = User(
        name=name.strip(),
        email=email,
        password_hash=hash_password(password),
        role="user",
        **{k: v for k, v in profile.items() if v not in (None, [])},
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, *, email: str, password: str) -> User:
    user = get_by_email(db, email)

    # Hash a throwaway password when the user does not exist, so a missing
    # account and a wrong password take the same amount of time.
    if user is None:
        verify_password(password, "$2b$12$" + "x" * 53)
        raise InvalidCredentials

    if not verify_password(password, user.password_hash):
        raise InvalidCredentials

    if user.is_blocked:
        raise AccountBlocked

    return user


def is_designated_admin_email(email: str) -> bool:
    from app.core.config import settings

    return bool(settings.admin_email) and email.strip().lower() == settings.admin_email


def sync_admin_role(db: Session, user: User) -> User:
    """Keep the admin role in line with the rule: admin if and only if this is
    the verified ADMIN_EMAIL account. Called on verify and login, so the owner
    becomes admin without any command, and anyone else who somehow holds the
    admin role loses it.

    Only the admin role is touched -- a business or regular account keeps its
    own role.
    """
    is_owner = user.is_verified and is_designated_admin_email(user.email)
    if is_owner and user.role != "admin":
        user.role = "admin"
    elif not is_owner and user.role == "admin":
        user.role = "user"
    else:
        return user
    db.commit()
    db.refresh(user)
    return user
