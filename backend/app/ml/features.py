"""The destination_features table: seeding it, reading it, and recognising a
destination in free text ("2 days in Fort Kochi" -> Kochi)."""
from __future__ import annotations

import math
import re

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.data.destinations import DESTINATIONS, STYLES
from app.models.destination import DestinationFeature


def ensure_seeded(db: Session) -> int:
    """Fill an empty table from the curated list. Returns rows added.

    Only an EMPTY table is seeded, so rows an admin edits or deletes in the
    database stay that way."""
    if db.scalar(select(func.count()).select_from(DestinationFeature)):
        return 0
    for d in DESTINATIONS:
        db.add(DestinationFeature(
            name=d.name, state=d.state, region=d.region, lat=d.lat, lng=d.lng,
            altitude_m=d.altitude_m, coastal=d.coastal, daily_cost=d.daily_cost,
            styles=dict(zip(STYLES, d.styles)), blurb=d.blurb, aliases=list(d.aliases),
            closed_months=list(d.closed_months), source="curated",
        ))
    db.commit()
    return len(DESTINATIONS)


def all_destinations(db: Session) -> list[DestinationFeature]:
    ensure_seeded(db)
    return list(db.scalars(select(DestinationFeature).order_by(DestinationFeature.name)))


def style_vector(row: DestinationFeature) -> list[float]:
    return [float(row.styles.get(s, 0.0)) for s in STYLES]


def _words(s: str) -> str:
    return " " + re.sub(r"[^a-z0-9]+", " ", s.lower()).strip() + " "


def match(rows: list[DestinationFeature], text: str) -> DestinationFeature | None:
    """The destination named in `text`, by name or alias, longest name first
    so "Fort Kochi" is not mistaken for something shorter."""
    hay = _words(text)
    names = sorted(
        ((n, row) for row in rows for n in [row.name, *row.aliases]),
        key=lambda pair: -len(pair[0]),
    )
    for name, row in names:
        if _words(name) in hay:
            return row
    return None


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0
