"""Trip request and response shapes."""
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.packing import ItemIn

TripStatus = Literal["processing", "completed", "failed"]
PlanStatus = Literal["draft", "saved", "upcoming", "completed"]

STYLE_TAGS = ("adventure", "relax", "culture", "food", "nature")
StyleTag = Literal["adventure", "relax", "culture", "food", "nature"]

MAX_TRIP_DAYS = 30


class TripCreate(BaseModel):
    destination: Annotated[str, Field(min_length=2, max_length=200)]
    start_date: date
    end_date: date
    budget: Annotated[Decimal, Field(gt=0, le=Decimal("10000000"))]
    travelers: Annotated[int, Field(ge=1, le=20)] = 1
    style_tags: Annotated[list[StyleTag], Field(max_length=len(STYLE_TAGS))] = []
    use_memory: bool = True

    @model_validator(mode="after")
    def check_dates(self) -> "TripCreate":
        if self.end_date < self.start_date:
            raise ValueError("end_date must not be before start_date")
        if (self.end_date - self.start_date).days + 1 > MAX_TRIP_DAYS:
            raise ValueError(f"Trips longer than {MAX_TRIP_DAYS} days are not supported")
        # Duplicates would skew the style vector in Phase 8's recommender.
        if len(set(self.style_tags)) != len(self.style_tags):
            raise ValueError("style_tags must not repeat")
        return self


class MemorySource(BaseModel):
    trip_id: uuid.UUID
    destination: str
    start_date: date
    similarity: float


class ItineraryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    day_plan: list[dict[str, Any]]
    budget_breakdown: dict[str, float]
    explanation: str | None
    memory_sources: list[MemorySource] | None = None
    # Think on the Plan -- see app/ml/think.py for the shape.
    thinking: dict[str, Any] | None = None


class TripRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    destination: str
    start_date: date
    end_date: date
    budget: Decimal
    travelers: int
    style_tags: list[str]
    use_memory: bool
    status: TripStatus
    plan_status: PlanStatus
    error: str | None
    created_at: datetime
    discoverable: bool = False
    source: Literal["ai", "manual", "copy"] = "ai"
    # Filled per viewer by the router.
    role: Literal["owner", "member"] = "owner"
    member_count: int = 0
    my_rating: int | None = None


class TripDetail(TripRead):
    itinerary: ItineraryRead | None = None


# --- plans the traveller writes, edits or reuses ----------------------------------

TIME_PATTERN = r"^$|^([01]\d|2[0-3]):[0-5]\d$"


class PlanItemIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    time: Annotated[str, Field(max_length=5, pattern=TIME_PATTERN)] = ""
    activity: Annotated[str, Field(min_length=1, max_length=200)]
    place: Annotated[str, Field(max_length=200)] = ""
    estimated_cost: Annotated[Decimal, Field(ge=0, le=Decimal("10000000"))] = Decimal(0)


class PlanDayIn(BaseModel):
    items: Annotated[list[PlanItemIn], Field(max_length=25)] = []


class OwnPlanCreate(BaseModel):
    """A plan written by the traveller. Budget is optional (0 = not set)."""
    destination: Annotated[str, Field(min_length=2, max_length=200)]
    start_date: date
    end_date: date
    budget: Annotated[Decimal, Field(ge=0, le=Decimal("10000000"))] = Decimal(0)
    travelers: Annotated[int, Field(ge=1, le=20)] = 1
    style_tags: Annotated[list[StyleTag], Field(max_length=len(STYLE_TAGS))] = []
    notes: Annotated[str | None, Field(max_length=2000)] = None
    days: Annotated[list[PlanDayIn], Field(max_length=MAX_TRIP_DAYS)] = []
    # What to take (or, for a past trip, what was taken). Goes on the packing list.
    packing: Annotated[list[ItemIn], Field(max_length=150)] = []

    @model_validator(mode="after")
    def check_dates(self) -> "OwnPlanCreate":
        if self.end_date < self.start_date:
            raise ValueError("end_date must not be before start_date")
        if (self.end_date - self.start_date).days + 1 > MAX_TRIP_DAYS:
            raise ValueError(f"Trips longer than {MAX_TRIP_DAYS} days are not supported")
        if len(set(self.style_tags)) != len(self.style_tags):
            raise ValueError("style_tags must not repeat")
        return self


class PlanUpdate(BaseModel):
    days: Annotated[list[PlanDayIn], Field(max_length=MAX_TRIP_DAYS)]
    notes: Annotated[str | None, Field(max_length=2000)] = None
    # None leaves the packing list alone; a list replaces the traveller's own items.
    packing: Annotated[list[ItemIn] | None, Field(max_length=150)] = None


class CopyRequest(BaseModel):
    start_date: date
