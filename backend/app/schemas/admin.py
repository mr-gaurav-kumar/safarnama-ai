"""Admin dashboard shapes (§4.14, §6.1)."""
from datetime import date, datetime
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.user import check_password_rules

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int


class Stats(BaseModel):
    users_total: int
    users_blocked: int
    signups_7d: int
    trips_total: int
    trips_active: int          # not over yet
    trips_processing: int
    open_fraud_flags: int
    open_escalations: int
    packages_active: int = 0
    bookings_pending: int = 0
    businesses_pending: int = 0


class AdminUser(BaseModel):
    id: str
    name: str
    email: str
    role: Literal["user", "admin", "business"]
    is_verified: bool
    is_blocked: bool
    created_at: datetime
    trip_count: int
    open_flags: int
    home_town: str | None = None
    avatar_url: str | None = None


class UserCreate(BaseModel):
    """Accounts made from the admin panel are always travellers: there is one
    admin, set from the command line, and the API never hands out the role."""

    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    is_verified: bool = False
    home_town: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=20)

    @field_validator("password")
    @classmethod
    def _alphanumeric(cls, v: str) -> str:
        return check_password_rules(v)


class UserUpdate(BaseModel):
    """No `role` here on purpose -- the admin panel cannot promote anyone."""

    name: str | None = Field(default=None, min_length=1, max_length=120)
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=8, max_length=72)
    is_blocked: bool | None = None
    is_verified: bool | None = None
    home_town: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=20)
    date_of_birth: date | None = None
    gender: Literal["male", "female", "other", "prefer_not"] | None = None

    @field_validator("password")
    @classmethod
    def _password_rules(cls, v: str | None) -> str | None:
        return None if v is None else check_password_rules(v)


class AdminTrip(BaseModel):
    id: str
    destination: str
    start_date: date
    end_date: date
    status: str
    plan_status: str
    owner_email: str
    member_count: int
    created_at: datetime
    error: str | None
    budget: float = 0
    travelers: int = 1
    style_tags: list[str] = []


class AdminTripDetail(BaseModel):
    id: str
    use_memory: bool = True
    destination: str
    start_date: date
    end_date: date
    status: str
    plan_status: str
    budget: float
    travelers: int
    style_tags: list[str]
    created_at: datetime


class AdminUserDetail(AdminUser):
    """Everything about one account, for the admin's user panel."""

    updated_at: datetime
    date_of_birth: date | None
    phone: str | None
    gender: str | None
    travel_interests: list[str] | None
    trips: list[AdminTripDetail]
    last_login_at: datetime | None
    login_count: int


class TripUpdate(BaseModel):
    status: Literal["processing", "completed", "failed"] | None = None
    plan_status: Literal["draft", "saved", "upcoming", "completed"] | None = None
    destination: str | None = Field(default=None, min_length=2, max_length=200)
    start_date: date | None = None
    end_date: date | None = None
    budget: float | None = Field(default=None, gt=0, le=10_000_000)
    travelers: int | None = Field(default=None, ge=1, le=20)
    style_tags: list[Literal["adventure", "relax", "culture", "food", "nature"]] | None = None


class AdminFlag(BaseModel):
    id: str
    user_id: str
    user_email: str
    user_blocked: bool
    trip_id: str | None
    reason: str
    risk_score: float
    details: dict[str, Any]
    status: str
    created_at: datetime
    reviewed_at: datetime | None


class FlagUpdate(BaseModel):
    status: Literal["open", "resolved", "dismissed"]
    block_user: bool = False


class AdminEscalation(BaseModel):
    id: str
    user_email: str
    reason: str
    intent: str | None
    excerpt: str
    status: str
    created_at: datetime


class EscalationUpdate(BaseModel):
    status: Literal["open", "resolved"]


class AdminFeedback(BaseModel):
    id: str
    trip_id: str
    destination: str
    user_email: str
    rating: int
    comment: str | None
    created_at: datetime


class AdminChatLine(BaseModel):
    id: str
    user_email: str
    sender: str
    message: str
    intent: str | None
    sentiment: str | None
    created_at: datetime


class AuditLine(BaseModel):
    id: str
    admin_email: str | None
    action: str
    target_type: str
    target_id: str
    details: dict[str, Any]
    created_at: datetime
