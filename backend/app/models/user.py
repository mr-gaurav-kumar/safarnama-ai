"""The users table -- §5.1 of the project document."""
import datetime as dt

from sqlalchemy import JSON, Boolean, Date, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class User(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "users"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # 'user' or 'admin' -- gates every /admin endpoint, checked server-side.
    role: Mapped[str] = mapped_column(String(20), default="user", nullable=False)

    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Google's permanent account id ("sub") once the user signs in with Google.
    # Keyed on this, not the email: a Google account's email can change.
    google_sub: Mapped[str | None] = mapped_column(String(255), unique=True, index=True, nullable=True)

    # Profile picture: a public /media/avatars/... path, or None for initials.
    avatar_url: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Profile, collected at sign-up. Nullable: accounts made before these
    # existed (and accounts an admin creates) have none.
    date_of_birth: Mapped[dt.date | None] = mapped_column(Date, nullable=True)
    home_town: Mapped[str | None] = mapped_column(String(120), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    gender: Mapped[str | None] = mapped_column(String(20), nullable=True)
    travel_interests: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    def __repr__(self) -> str:
        return f"<User {self.email} role={self.role}>"
