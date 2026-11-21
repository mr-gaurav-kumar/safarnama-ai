"""Phase 8 request/response shapes: budget recommender and Think on the Plan."""
from datetime import date
from decimal import Decimal
from typing import Annotated, Any

from pydantic import BaseModel, Field, model_validator

from app.schemas.trip import MAX_TRIP_DAYS, STYLE_TAGS, StyleTag


class BudgetRequest(BaseModel):
    budget: Annotated[Decimal, Field(gt=0, le=Decimal("10000000"))]
    days: Annotated[int, Field(ge=1, le=MAX_TRIP_DAYS)]
    travelers: Annotated[int, Field(ge=1, le=20)] = 1
    month: Annotated[int | None, Field(ge=1, le=12)] = None
    style_tags: Annotated[list[StyleTag], Field(max_length=len(STYLE_TAGS))] = []
    # Let the traveller's rated trips shape the ranking (the default).
    use_memory: bool = True
    limit: Annotated[int, Field(ge=1, le=20)] = 6
    # Where the trip starts ("Ghaziabad, Uttar Pradesh"). The page always
    # sends it; older callers may not.
    origin: Annotated[str | None, Field(max_length=120)] = None
    # Optional: a place ("Manali") or a state / region ("Himachal Pradesh").
    destination: Annotated[str | None, Field(max_length=120)] = None

    @model_validator(mode="after")
    def no_repeats(self) -> "BudgetRequest":
        if len(set(self.style_tags)) != len(self.style_tags):
            raise ValueError("style_tags must not repeat")
        return self


class Recommendation(BaseModel):
    name: str
    state: str
    blurb: str
    score: float
    style_match: float
    budget_fit: float
    daily_cost: int
    season: str | None
    season_confidence: float | None
    styles: dict[str, float]
    reasons: list[str]
    visited: bool
    distance_km: int | None = None
    travel_mode: str | None = None
    travel_fare: int | None = None  # per person, there and back
    # {"total", "verdict", "travel", "stay", "food", "local"} when we know where they start
    estimate: dict | None = None
    is_destination: bool = False


class BudgetResponse(BaseModel):
    per_person_per_day: int
    on_ground_per_day: int
    travel_share: float
    considered: int
    over_budget: int
    closed: int
    taste: list[str]
    items: list[Recommendation]
    note: str
    origin: str | None = None
    origin_found: bool = False
    # How "to" was read: a place and the places near it, a state, or not found.
    destination_mode: str | None = None
    destination_note: str | None = None


class ThinkRequest(BaseModel):
    destination: Annotated[str, Field(min_length=2, max_length=200)]
    start_date: date
    end_date: date
    budget: Annotated[Decimal, Field(gt=0, le=Decimal("10000000"))]
    travelers: Annotated[int, Field(ge=1, le=20)] = 1
    style_tags: Annotated[list[StyleTag], Field(max_length=len(STYLE_TAGS))] = []

    @model_validator(mode="after")
    def check_dates(self) -> "ThinkRequest":
        if self.end_date < self.start_date:
            raise ValueError("end_date must not be before start_date")
        if (self.end_date - self.start_date).days + 1 > MAX_TRIP_DAYS:
            raise ValueError(f"Trips longer than {MAX_TRIP_DAYS} days are not supported")
        return self


ThinkResponse = dict[str, Any]
