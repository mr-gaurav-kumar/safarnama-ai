"""Travel packages and bookings -- request and response shapes."""
import re
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

PackageTag = Literal["adventure", "relax", "culture", "food", "nature", "spiritual", "shopping", "nightlife"]
BookingStatus = Literal["pending", "confirmed", "cancelled"]
PACKAGE_TAGS = ("adventure", "relax", "culture", "food", "nature", "spiritual", "shopping", "nightlife")


class PackageFillIn(BaseModel):
    """A package being written: what is known so far. Only the destination,
    length and price are needed; anything left blank can be suggested."""
    title: str = Field(default="", max_length=160)
    destination: str = Field(min_length=2, max_length=200)
    duration_days: int = Field(ge=1, le=60)
    price_per_person: float = Field(gt=0, le=10_000_000)
    summary: str = Field(default="", max_length=300)
    description: str = Field(default="", max_length=5000)
    inclusions: list[str] = Field(default_factory=list, max_length=20)
    highlights: list[str] = Field(default_factory=list, max_length=30)
    style_tags: list[PackageTag] = Field(default_factory=list, max_length=8)


MEDIA_URL_RE = re.compile(r"/media/packages/[0-9a-f]{32}\.(jpg|png|webp)")


def _clean_list(items: list[str]) -> list[str]:
    out = [" ".join(i.split()) for i in items]
    return [i for i in dict.fromkeys(out) if i]


class PackageIn(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    destination: str = Field(min_length=2, max_length=200)
    duration_days: int = Field(ge=1, le=60)
    price_per_person: float = Field(gt=0, le=10_000_000)
    summary: str = Field(default="", max_length=300)
    description: str = Field(default="", max_length=5000)
    inclusions: list[str] = Field(default_factory=list, max_length=20)
    highlights: list[str] = Field(default_factory=list, max_length=30)
    style_tags: list[PackageTag] = Field(default_factory=list, max_length=8)
    images: list[str] = Field(default_factory=list, max_length=10)
    seats: int | None = Field(default=None, ge=1, le=10_000)
    valid_from: date | None = None
    valid_until: date | None = None
    is_active: bool = True

    @field_validator("inclusions", "highlights")
    @classmethod
    def _tidy(cls, v: list[str]) -> list[str]:
        return _clean_list(v)

    @field_validator("style_tags")
    @classmethod
    def _unique(cls, v: list[str]) -> list[str]:
        return list(dict.fromkeys(v))

    @field_validator("images")
    @classmethod
    def _images(cls, v: list[str]) -> list[str]:
        out = []
        for url in dict.fromkeys(u.strip() for u in v):
            if not url:
                continue
            if not (MEDIA_URL_RE.fullmatch(url) or (url.startswith("https://") and len(url) <= 500)):
                raise ValueError("Images must be uploaded files or https:// links")
            out.append(url)
        return out

    @model_validator(mode="after")
    def _window(self) -> "PackageIn":
        if self.valid_from and self.valid_until and self.valid_until < self.valid_from:
            raise ValueError("valid_until must not be before valid_from")
        return self


class PackageOut(BaseModel):
    id: str
    title: str
    destination: str
    duration_days: int
    price_per_person: float
    summary: str
    description: str
    inclusions: list[str]
    highlights: list[str]
    style_tags: list[str]
    images: list[str] = []
    seats: int | None
    seats_left: int | None
    valid_from: date | None
    valid_until: date | None
    is_active: bool
    created_at: datetime
    booking_count: int = 0
    # Who runs it: null for the platform's own packages.
    business_name: str | None = None
    business_slug: str | None = None


class BookingIn(BaseModel):
    travelers: int = Field(ge=1, le=20)
    start_date: date
    note: str | None = Field(default=None, max_length=500)


class BookingOut(BaseModel):
    id: str
    package_id: str
    package_title: str
    destination: str
    duration_days: int
    travelers: int
    start_date: date
    end_date: date
    total_price: float
    note: str | None
    status: str
    created_at: datetime
    user_name: str | None = None
    user_email: str | None = None


class BookingStatusIn(BaseModel):
    status: BookingStatus
