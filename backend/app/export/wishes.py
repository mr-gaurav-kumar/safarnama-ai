"""The good-luck message printed on every exported plan.

Each download draws a fresh one: an opening line about the place, one line
that fits this trip (its season, its style, or who is going), and a sign-off.
With these lists that is several hundred combinations, so two downloads of the
same plan almost never read the same -- and every one still fits the trip.
"""
from __future__ import annotations

import random
from dataclasses import dataclass

_rng = random.SystemRandom()

OPENERS = (
    "Pack light, wander far: {dest} is waiting for you.",
    "{dest} has been expecting you.",
    "May every turn in {dest} bring a better view than the last.",
    "The best stories start with a ticket. Yours starts in {dest}.",
    "Go slow, look up, and let {dest} surprise you.",
    "Safar mubarak! {dest} is going to be good to you.",
    "Window seat, full heart, open plans. Enjoy {dest}.",
    "Somewhere in {dest} is a moment you will talk about for years.",
    "Leave a little room in your bag for memories from {dest}.",
    "Every safar is a new page. Make {dest} a good chapter.",
    "Chai at sunrise, stories at sunset. Have a beautiful time in {dest}.",
    "New roads, new food, new friends. {dest} has all three.",
    "Here is to getting a little lost in {dest}, and loving it.",
    "Put the phone down once in a while. {dest} is better seen than scrolled.",
)

SEASON_LINES = {
    "ideal": (
        "You picked one of the best times of the year to go.",
        "Great timing: this is when {dest} is at its best.",
    ),
    "pleasant": (
        "The weather should be kind to you, so make the most of it.",
        "Pleasant days ahead. Spend them outdoors.",
    ),
    "hot": (
        "It will be warm: start early, rest at noon and keep water close.",
        "Sunscreen on, water bottle full, and the mornings are yours.",
    ),
    "rainy": (
        "It is monsoon season. Carry a light rain jacket and let the rain add to the magic.",
        "Rain makes everything greener. Keep your plans loose and your shoes waterproof.",
    ),
    "cold": (
        "It will be chilly, so layer up and keep a hot drink close.",
        "Cold air, clear views. Wrap up warm and enjoy every minute.",
    ),
}

STYLE_LINES = {
    "adventure": "May your adventures be thrilling and your landings soft.",
    "food": "Eat like a local and never skip dessert.",
    "culture": "Every old wall has a story. Stop and listen to a few.",
    "nature": "Breathe deep. The outdoors is the whole point.",
    "relax": "No alarms, unless it is for the sunrise.",
}

GROUP_LINES = (
    "Travel well together. The shared moments are the ones you will remember.",
    "Good company makes every road shorter. Enjoy the ride together.",
)
SOLO_LINES = (
    "Solo trips teach the best lessons. Trust yourself.",
    "Just you and the road. Enjoy the freedom.",
)

CLOSERS = (
    "Have a wonderful trip!",
    "Happy travels!",
    "Safe travels and happy memories.",
    "Shubh yatra!",
    "Come back with stories.",
    "Bon voyage!",
)

SIGNATURE = "Team Safarnama"


@dataclass(frozen=True)
class Wish:
    text: str
    signature: str = SIGNATURE


def wish_for(destination: str, season: str | None = None, styles: list[str] | None = None,
             travelers: int = 1, rng: random.Random | None = None) -> Wish:
    r = rng or _rng
    dest = (destination or "your destination").split(",")[0].strip() or "your destination"

    middles: list[str] = list(SEASON_LINES.get(season or "", ()))
    middles += [STYLE_LINES[s] for s in (styles or []) if s in STYLE_LINES]
    middles += list(GROUP_LINES if travelers > 1 else SOLO_LINES)

    parts = [r.choice(OPENERS), r.choice(middles), r.choice(CLOSERS)]
    return Wish(" ".join(p.format(dest=dest) for p in parts))
