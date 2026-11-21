"""Packing list requests and responses."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

Category = Literal["clothes", "footwear", "toiletries", "documents", "electronics", "health", "accessories", "other"]
Source = Literal["mine", "ai", "admin"]


def _tidy(v: str) -> str:
    v = " ".join(v.split())
    if not v:
        raise ValueError("Give the item a name")
    return v


class ItemIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    category: Category = "other"
    quantity: int = Field(default=1, ge=1, le=99)

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        return _tidy(v)


class BulkIn(BaseModel):
    """Several items at once -- the AI suggestions the traveller picked."""

    items: list[ItemIn] = Field(min_length=1, max_length=60)
    source: Literal["mine", "ai"] = "ai"


class ItemUpdate(BaseModel):
    """Only the fields sent change. Admin items: only the two ticks."""

    name: str | None = Field(default=None, min_length=1, max_length=80)
    category: Category | None = None
    quantity: int | None = Field(default=None, ge=1, le=99)
    packed_going: bool | None = None
    packed_return: bool | None = None

    @field_validator("name")
    @classmethod
    def _name(cls, v: str | None) -> str | None:
        return None if v is None else _tidy(v)


class ItemOut(BaseModel):
    id: str
    name: str
    category: str
    quantity: int
    packed_going: bool
    packed_return: bool
    source: Source
    locked: bool  # admin item: the traveller can tick it but not change or remove it
    note: str | None = None


class Progress(BaseModel):
    total: int
    packed_going: int
    packed_return: int


class PackingList(BaseModel):
    trip_id: str
    destination: str
    start_date: str
    end_date: str
    items: list[ItemOut]
    progress: Progress


class Suggestion(BaseModel):
    name: str
    category: Category
    quantity: int
    reason: str


class Suggestions(BaseModel):
    items: list[Suggestion]
    # "ai" when Gemini wrote them, "rules" for the built-in packing rules.
    source: Literal["ai", "rules"]
    context: list[str]  # what the suggestions were based on, shown to the user


# --- admin ------------------------------------------------------------------

class DefaultIn(ItemIn):
    note: str | None = Field(default=None, max_length=200)
    # Empty = every traveller; an email = only that person.
    user_email: EmailStr | None = None


class DefaultUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    category: Category = "other"
    quantity: int = Field(default=1, ge=1, le=99)
    note: str | None = Field(default=None, max_length=200)

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        return _tidy(v)


class DefaultOut(BaseModel):
    id: str
    name: str
    category: str
    quantity: int
    note: str | None
    user_id: str | None
    user_email: str | None  # null = everyone
    user_name: str | None
    created_at: datetime
