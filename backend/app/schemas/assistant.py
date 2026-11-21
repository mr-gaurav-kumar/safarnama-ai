"""Travel assistant requests and replies."""
from typing import Literal

from pydantic import BaseModel, Field


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    text: str = Field(max_length=2000)


class AssistantRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500)
    # The last few turns, so "make it 5 days" builds on the question before.
    history: list[ChatTurn] = Field(default_factory=list, max_length=12)


class Understood(BaseModel):
    budget: int | None
    days: int
    travelers: int
    month: int
    month_name: str
    origin: str | None
    moods: list[str]
    # What we filled in because the question didn't say.
    assumed: list[str]
    when: str | None = None  # weekend | long_weekend | weekdays


class Pick(BaseModel):
    name: str
    state: str
    blurb: str
    reasons: list[str]
    # {"label": ideal|pleasant|hot|rainy|cold, "text": ..., "confidence": 0-1}
    season: dict
    # Next 7 days when the trip is this month: {"high", "low", "rain_chance", "rainy_days", ...}
    live: dict | None
    # {"travel_mode", "travel", "stay", "food", "local", "total", "per_person", "verdict", "distance_km"}
    estimate: dict
    altitude_m: int
    coastal: bool
    # Query params for /trips/new
    plan: dict


class AssistantReply(BaseModel):
    reply: str
    intent: Literal["recommend", "place", "unknown", "help"]
    understood: Understood
    picks: list[Pick]
    from_model: bool
