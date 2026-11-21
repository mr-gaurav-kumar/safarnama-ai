"""Request and response shapes for authentication.

A password never appears in a response model, so it cannot leak by accident.
"""
import datetime as dt
import re
import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

Role = Literal["user", "admin", "business"]


Gender = Literal["male", "female", "other", "prefer_not"]
Interest = Literal["adventure", "relax", "culture", "food", "nature", "spiritual", "shopping", "nightlife"]

MIN_AGE = 13


def check_password_rules(v: str) -> str:
    """At least 8 characters, with at least one letter and one number."""
    if len(v) < 8:
        raise ValueError("Password must be at least 8 characters")
    if not re.search(r"[A-Za-z]", v) or not re.search(r"\d", v):
        raise ValueError("Password must contain both letters and numbers")
    return v


class ProfileFields(BaseModel):
    """Profile details shared by sign-up and the profile page. All optional in
    the API (older clients, admin-created accounts); the sign-up page asks for
    date of birth and home town."""

    date_of_birth: dt.date | None = None
    home_town: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=20)
    gender: Gender | None = None
    travel_interests: list[Interest] = Field(default_factory=list, max_length=8)

    @field_validator("date_of_birth")
    @classmethod
    def _age(cls, v: dt.date | None) -> dt.date | None:
        if v is None:
            return v
        today = dt.date.today()
        if v >= today:
            raise ValueError("Date of birth must be in the past")
        age = today.year - v.year - ((today.month, today.day) < (v.month, v.day))
        if age < MIN_AGE:
            raise ValueError(f"You must be at least {MIN_AGE} to sign up")
        if age > 120:
            raise ValueError("Please check the date of birth")
        return v

    @field_validator("home_town")
    @classmethod
    def _town(cls, v: str | None) -> str | None:
        v = " ".join(v.split()) if v else None
        return v or None

    @field_validator("phone")
    @classmethod
    def _phone(cls, v: str | None) -> str | None:
        if not v or not v.strip():
            return None
        digits = re.sub(r"[\s\-()]", "", v)
        if not re.fullmatch(r"\+?\d{10,15}", digits):
            raise ValueError("Enter a valid phone number")
        return digits

    @field_validator("travel_interests")
    @classmethod
    def _unique(cls, v: list[str]) -> list[str]:
        return list(dict.fromkeys(v))


class SignupRequest(ProfileFields):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)

    @field_validator("password")
    @classmethod
    def _alphanumeric(cls, v: str) -> str:
        return check_password_rules(v)


class ProfileUpdate(ProfileFields):
    """PUT /auth/me. Only the fields sent are changed."""

    name: str | None = Field(default=None, min_length=1, max_length=120)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=72)
    new_password: str = Field(min_length=8, max_length=72)

    @field_validator("new_password")
    @classmethod
    def _alphanumeric(cls, v: str) -> str:
        return check_password_rules(v)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=10, max_length=2000)
    password: str = Field(min_length=8, max_length=72)

    @field_validator("password")
    @classmethod
    def _alphanumeric(cls, v: str) -> str:
        return check_password_rules(v)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    email: EmailStr
    role: Role
    is_verified: bool
    date_of_birth: dt.date | None = None
    home_town: str | None = None
    phone: str | None = None
    gender: str | None = None
    travel_interests: list[str] | None = None
    avatar_url: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead
