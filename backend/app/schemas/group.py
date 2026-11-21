"""Group trips, invitations, matches and feedback."""
from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, EmailStr, Field

from app.schemas.trip import StyleTag


class InviteRequest(BaseModel):
    email: EmailStr


class JoinRequest(BaseModel):
    token: str | None = None


class PreferencesRequest(BaseModel):
    style_tags: Annotated[list[StyleTag], Field(max_length=5)]


class DiscoverableRequest(BaseModel):
    discoverable: bool


class MemberOut(BaseModel):
    id: str | None
    name: str | None
    email: str
    role: Literal["owner", "member", "invited", "declined"]
    style_tags: list[str]
    is_you: bool


class InvitationOut(BaseModel):
    trip_id: str
    destination: str
    start_date: date
    end_date: date
    invited_by: str


class MatchOut(BaseModel):
    trip_id: str
    first_name: str
    start_date: date
    end_date: date
    overlap_days: int
    already_requested: bool


class FeedbackRequest(BaseModel):
    rating: Annotated[int, Field(ge=1, le=5)]
    comment: Annotated[str | None, Field(max_length=1000)] = None


class FeedbackMine(BaseModel):
    rating: int
    comment: str | None


class FeedbackSummary(BaseModel):
    can_rate: bool
    mine: FeedbackMine | None
    count: int
    average: float | None
