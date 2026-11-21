"""Business / agency accounts."""
import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.user import SignupRequest, check_password_rules

BusinessKind = Literal["agency", "tour_operator", "hotel", "other"]
BusinessStatus = Literal["pending", "approved", "rejected", "suspended"]

GST_RE = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")


class BusinessFields(BaseModel):
    business_name: str = Field(min_length=2, max_length=160)
    kind: BusinessKind = "agency"
    city: str = Field(min_length=2, max_length=120)
    business_phone: str = Field(min_length=10, max_length=20)
    description: str = Field(default="", max_length=2000)
    website: str | None = Field(default=None, max_length=200)
    gst_number: str | None = Field(default=None, max_length=15)

    @field_validator("business_name", "city")
    @classmethod
    def _squash(cls, v: str) -> str:
        return " ".join(v.split())

    @field_validator("business_phone")
    @classmethod
    def _phone(cls, v: str) -> str:
        digits = re.sub(r"[\s\-()]", "", v)
        if not re.fullmatch(r"\+?\d{10,15}", digits):
            raise ValueError("Enter a valid business phone number")
        return digits

    @field_validator("gst_number")
    @classmethod
    def _gst(cls, v: str | None) -> str | None:
        if not v or not v.strip():
            return None
        v = v.strip().upper()
        if not GST_RE.fullmatch(v):
            raise ValueError("Enter a valid 15-character GSTIN, or leave it blank")
        return v

    @field_validator("website")
    @classmethod
    def _site(cls, v: str | None) -> str | None:
        if not v or not v.strip():
            return None
        v = v.strip()
        return v if v.startswith(("http://", "https://")) else f"https://{v}"


class BusinessSignupRequest(SignupRequest, BusinessFields):
    """Personal account details (the owner) plus the business."""


class BusinessUpdate(BusinessFields):
    pass


class BusinessOut(BaseModel):
    user_id: str
    business_name: str
    slug: str
    kind: str
    city: str
    business_phone: str
    description: str
    website: str | None
    gst_number: str | None
    status: str
    status_reason: str | None
    created_at: datetime
    reviewed_at: datetime | None
    owner_name: str | None = None
    owner_email: str | None = None
    package_count: int = 0
    bookings_pending: int = 0
    # The owner's login is blocked: nothing of theirs is shown to anyone.
    owner_blocked: bool = False
    # Approved and not blocked -- i.e. travellers can see its packages.
    is_visible: bool = False


class BusinessPublic(BaseModel):
    business_name: str
    slug: str
    kind: str
    city: str
    description: str
    website: str | None
    since: datetime


class AdminBusinessCreate(BusinessFields):
    """A merchant account made by the admin: the owner's login plus the business."""

    owner_name: str = Field(min_length=1, max_length=120)
    owner_email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    is_verified: bool = True
    # Admin-made merchants are usually vetted already, so live straight away.
    status: BusinessStatus = "approved"

    @field_validator("password")
    @classmethod
    def _password(cls, v: str) -> str:
        return check_password_rules(v)


class BusinessBlockIn(BaseModel):
    blocked: bool
    reason: str | None = Field(default=None, max_length=300)


class BusinessStatusIn(BaseModel):
    status: BusinessStatus
    reason: str | None = Field(default=None, max_length=300)
