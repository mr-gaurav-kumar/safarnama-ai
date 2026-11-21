"""Packing lists: reading and changing a traveller's list, the admin's default
items, and suggestions for what to pack.

Suggestions come from Gemini when GEMINI_API_KEY is set, and from the packing
rules below otherwise (or if the model fails). Both look at the same facts:
how many days, the season the trip falls in (the Random Forest season model
from Think on the Plan), whether the place is on the coast or high up, and
the trip's styles.
"""
from __future__ import annotations

import json
import logging
import math
import uuid
from dataclasses import dataclass

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.packing import CATEGORIES, PackingDefault, PackingItem
from app.models.trip import Trip
from app.models.user import User
from app.schemas.packing import ItemIn, ItemOut, ItemUpdate, PackingList, Progress, Suggestion, Suggestions

logger = logging.getLogger(__name__)

MAX_ITEMS_PER_LIST = 200


class PackingError(Exception):
    """A request we refuse, with a sentence for the traveller."""


class ItemLocked(PackingError):
    pass


class ItemNotFound(PackingError):
    pass


# ---------------------------------------------------------------- the list

def _defaults_for(db: Session, user_id: uuid.UUID) -> list[PackingDefault]:
    return list(db.scalars(
        select(PackingDefault)
        .where(or_(PackingDefault.user_id.is_(None), PackingDefault.user_id == user_id))
        .order_by(PackingDefault.created_at)
    ))


def sync_defaults(db: Session, trip: Trip, user_id: uuid.UUID) -> None:
    """Make sure every admin default that applies to this person is on their
    list, and that admin items still say what the admin last wrote."""
    defaults = _defaults_for(db, user_id)
    have = {
        i.default_id: i
        for i in db.scalars(select(PackingItem).where(
            PackingItem.trip_id == trip.id, PackingItem.user_id == user_id, PackingItem.default_id.is_not(None),
        ))
    }
    changed = False
    for d in defaults:
        item = have.get(d.id)
        if item is None:
            db.add(PackingItem(
                trip_id=trip.id, user_id=user_id, name=d.name, category=d.category,
                quantity=d.quantity, source="admin", default_id=d.id,
            ))
            changed = True
        elif (item.name, item.category, item.quantity) != (d.name, d.category, d.quantity):
            item.name, item.category, item.quantity = d.name, d.category, d.quantity
            changed = True
    if changed:
        db.commit()


def _items(db: Session, trip_id: uuid.UUID, user_id: uuid.UUID) -> list[PackingItem]:
    return list(db.scalars(
        select(PackingItem)
        .where(PackingItem.trip_id == trip_id, PackingItem.user_id == user_id)
        .order_by(PackingItem.created_at)
    ))


def _out(i: PackingItem, notes: dict[uuid.UUID, str | None]) -> ItemOut:
    return ItemOut(
        id=str(i.id), name=i.name, category=i.category, quantity=i.quantity,
        packed_going=i.packed_going, packed_return=i.packed_return, source=i.source,  # type: ignore[arg-type]
        locked=i.default_id is not None, note=notes.get(i.default_id) if i.default_id else None,
    )


def get_list(db: Session, trip: Trip, user_id: uuid.UUID) -> PackingList:
    sync_defaults(db, trip, user_id)
    items = _items(db, trip.id, user_id)
    notes = {d.id: d.note for d in _defaults_for(db, user_id)}
    order = {c: n for n, c in enumerate(CATEGORIES)}
    items.sort(key=lambda i: (order.get(i.category, 99), i.default_id is None, i.created_at))
    return PackingList(
        trip_id=str(trip.id), destination=trip.destination,
        start_date=trip.start_date.isoformat(), end_date=trip.end_date.isoformat(),
        items=[_out(i, notes) for i in items],
        progress=Progress(
            total=len(items),
            packed_going=sum(i.packed_going for i in items),
            packed_return=sum(i.packed_return for i in items),
        ),
    )


def add_items(db: Session, trip: Trip, user_id: uuid.UUID, items: list[ItemIn], source: str) -> int:
    """Adds the items not already on the list (same name, any case). Returns
    how many were added."""
    existing = _items(db, trip.id, user_id)
    if len(existing) + len(items) > MAX_ITEMS_PER_LIST:
        raise PackingError(f"A packing list can hold up to {MAX_ITEMS_PER_LIST} items.")
    names = {i.name.casefold() for i in existing}
    added = 0
    for it in items:
        if it.name.casefold() in names:
            continue
        names.add(it.name.casefold())
        db.add(PackingItem(
            trip_id=trip.id, user_id=user_id, name=it.name, category=it.category,
            quantity=it.quantity, source=source,
        ))
        added += 1
    db.commit()
    return added


def _own_item(db: Session, trip: Trip, user_id: uuid.UUID, item_id: uuid.UUID) -> PackingItem:
    item = db.get(PackingItem, item_id)
    # The same answer for "no such item" and "someone else's item".
    if item is None or item.trip_id != trip.id or item.user_id != user_id:
        raise ItemNotFound("Item not found")
    return item


def update_item(db: Session, trip: Trip, user_id: uuid.UUID, item_id: uuid.UUID, change: ItemUpdate) -> None:
    item = _own_item(db, trip, user_id, item_id)
    fields = change.model_dump(exclude_none=True)
    if item.default_id is not None and set(fields) - {"packed_going", "packed_return"}:
        raise ItemLocked("This item was added by the admin. You can tick it, but not change or remove it.")
    for k, v in fields.items():
        setattr(item, k, v)
    db.commit()


def delete_item(db: Session, trip: Trip, user_id: uuid.UUID, item_id: uuid.UUID) -> None:
    item = _own_item(db, trip, user_id, item_id)
    if item.default_id is not None:
        raise ItemLocked("This item was added by the admin, so only the admin can remove it.")
    db.delete(item)
    db.commit()


def reset_ticks(db: Session, trip: Trip, user_id: uuid.UUID, which: str) -> None:
    """Untick everything for 'going' or 'return' -- to start the check again."""
    field = PackingItem.packed_going if which == "going" else PackingItem.packed_return
    for item in _items(db, trip.id, user_id):
        setattr(item, field.key, False)
    db.commit()


# ---------------------------------------------------------------- suggestions

@dataclass
class TripFacts:
    destination: str
    days: int
    seasons: list[str]  # ideal | pleasant | hot | rainy | cold, one per month the trip touches
    coastal: bool
    altitude_m: int
    styles: list[str]
    month_names: list[str]

    def lines(self) -> list[str]:
        out = [f"{self.days} day{'s' if self.days > 1 else ''} in {self.destination}"]
        if self.seasons:
            out.append(f"{', '.join(self.month_names)}: {' then '.join(dict.fromkeys(self.seasons))} weather (season model)")
        if self.coastal:
            out.append("On the coast")
        if self.altitude_m >= 1500:
            out.append(f"High altitude (~{self.altitude_m:,} m)")
        if self.styles:
            out.append(f"Trip style: {', '.join(self.styles)}")
        return out


MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def trip_facts(db: Session, trip: Trip) -> TripFacts:
    days = (trip.end_date - trip.start_date).days + 1
    seasons: list[str] = []
    months: list[str] = []
    coastal, altitude = False, 0
    thinking = trip.itinerary.thinking if trip.itinerary is not None else None
    try:
        from app.ml import think

        row, _coords, _how = think._locate(db, trip.destination)  # noqa: SLF001 -- same module family
        if row is not None:
            coastal, altitude = bool(row.coastal), int(row.altitude_m)
        if not thinking:
            thinking = think.think_about_trip(
                db, destination=trip.destination, start_date=trip.start_date, end_date=trip.end_date,
                budget=float(trip.budget), travelers=trip.travelers, style_tags=list(trip.style_tags or []),
            )
    except Exception:  # noqa: BLE001 -- the season is a help; packing works without it
        logger.exception("Could not read the season for trip %s", trip.id)
        db.rollback()
    for s in (thinking or {}).get("seasons", []):
        seasons.append(s["label"])
        months.append(MONTHS[s["month"] - 1])
    return TripFacts(
        destination=trip.destination.split(",")[0].strip(), days=days, seasons=seasons,
        coastal=coastal, altitude_m=altitude, styles=list(trip.style_tags or []), month_names=months,
    )


def rule_suggestions(f: TripFacts) -> list[Suggestion]:
    """Plain packing rules -- the same list a careful friend would write."""
    n = max(1, f.days)
    s = set(f.seasons)
    cold = "cold" in s or f.altitude_m >= 2500
    hot = bool(s & {"hot"}) or (f.coastal and not cold)
    rainy = "rainy" in s
    sunny = bool(s & {"hot", "ideal", "pleasant"}) or f.coastal or f.altitude_m >= 2000
    outdoors = bool({"adventure", "nature"} & set(f.styles)) or f.altitude_m >= 1500
    laundry = " — plan one laundry stop" if n > 7 else ""
    out: list[Suggestion] = []

    def add(name: str, cat: str, qty: int, reason: str) -> None:
        out.append(Suggestion(name=name, category=cat, quantity=max(1, min(qty, 99)), reason=reason))  # type: ignore[arg-type]

    # clothes -- what kind of top depends on the weather
    if cold:
        add("Full-sleeve T-shirts", "clothes", min(n, 7), f"Cold weather — one per day{laundry}")
    elif hot:
        add("Half-sleeve cotton T-shirts", "clothes", min(n, 7), f"Hot weather — breathable, one per day{laundry}")
    else:
        add("T-shirts / tops", "clothes", min(n, 7), f"One per day{laundry}")
    add("Underwear", "clothes", min(n + 1, 8), f"One per day plus a spare{laundry}")
    add("Socks (pairs)", "clothes", min(n + 1, 8), "One pair per day plus a spare")
    add("Jeans / trousers", "clothes", min(3, max(1, math.ceil(n / 3))), "One for every ~3 days")
    add("Sleepwear", "clothes", 1 if n <= 4 else 2, "For the nights")
    if cold:
        add("Thermal inner set", "clothes", min(3, max(1, math.ceil(n / 3))), "Cold weather / high altitude")
        add("Heavy jacket", "clothes", 1, "Cold weather / high altitude")
        add("Sweater / fleece", "clothes", 1, "Layer under the jacket")
        add("Woollen cap", "clothes", 1, "Cold weather")
        add("Gloves (pair)", "clothes", 1, "Cold weather")
        add("Muffler / scarf", "clothes", 1, "Cold weather")
        add("Woollen socks (pairs)", "clothes", 2, "Cold nights")
    elif not hot:
        add("Light jacket / sweatshirt", "clothes", 1, "Evenings can be cool")
    if hot:
        add("Shorts", "clothes", 2, "Warm weather")
        add("Light cotton / linen pants", "clothes", 1, "Cool in the heat, covers legs from sun")
        add("Cap / hat", "accessories", 1, "Sun protection")
    if f.coastal:
        add("Swimwear", "clothes", 1, "Beach / pool")
    if rainy:
        add("Raincoat / poncho", "clothes", 1, "Rainy season")
        add("Umbrella", "accessories", 1, "Rainy season")
        add("Zip-lock / plastic bags", "accessories", 4, "Keep phone and wet clothes separate")
    if "culture" in f.styles:
        add("Modest outfit for temples", "clothes", 1, "Shoulders and knees covered at religious places")

    # footwear
    add("Comfortable walking shoes", "footwear", 1, "Most days involve walking")
    add("Slippers / flip-flops", "footwear", 1, "Hotel, bathroom and beach")
    if cold and f.altitude_m >= 2000:
        add("Waterproof boots", "footwear", 1, "Snow, slush and cold ground in the hills")
    elif outdoors:
        add("Trekking shoes / boots", "footwear", 1, "Hilly trails and uneven ground")
    if hot or f.coastal:
        add("Sandals / floaters", "footwear", 1, "Hot days and beaches")

    # toiletries
    for name in ("Toothbrush", "Toothpaste", "Soap / body wash", "Shampoo", "Face wash", "Deodorant", "Comb / hairbrush"):
        add(name, "toiletries", 1, "Daily basics")
    add("Towel", "toiletries", 1, "Not every stay gives one")
    add("Hand sanitiser", "toiletries", 1, "Travel days and street food")
    add("Tissues / wet wipes", "toiletries", 1, "Travel days")
    if sunny:
        add("Sunscreen", "toiletries", 1, "Strong sun" + (" at altitude" if f.altitude_m >= 2000 else ""))
        add("Sunglasses", "accessories", 1, "Strong sun")
    if cold:
        add("Lip balm", "toiletries", 1, "Cold, dry air")
        add("Moisturiser / cold cream", "toiletries", 1, "Cold, dry air")
    if rainy or f.coastal or "nature" in f.styles:
        add("Mosquito repellent", "toiletries", 1, "Rain, coast or forests")

    # documents and money
    add("Government photo ID", "documents", 1, "Hotels and airports ask for it")
    add("Tickets & hotel bookings (phone + printout)", "documents", 1, "In case the phone dies")
    add("Debit / credit card", "documents", 1, "Payments")
    add("Some cash", "documents", 1, "Small shops, autos and tips")

    # electronics
    add("Phone charger", "electronics", 1, "Daily")
    add("Power bank", "electronics", 1, "Long travel days")
    add("Earphones", "electronics", 1, "Journeys")
    if outdoors:
        add("Torch / headlamp", "electronics", 1, "Early starts and dark trails")

    # health
    add("Your regular medicines", "health", 1, f"Enough for {n + 2} days, in your hand luggage")
    add("Basic first-aid kit", "health", 1, "Plasters, antiseptic, pain relief")
    if hot:
        add("ORS sachets", "health", 4, "Hot weather — stay hydrated")

    # accessories
    add("Daypack / small backpack", "accessories", 1, "For day trips")
    add("Reusable water bottle", "accessories", 1, "Refill instead of buying plastic")
    return out


_PROMPT = """You are helping a traveller from India pack for a trip.

Trip facts:
{facts}

Return JSON only: {{"items": [{{"name": str, "category": one of {cats}, "quantity": int, "reason": str}}]}}
Rules: 25-45 items for ONE person. Quantities fit the number of days (assume one laundry stop for trips over a week).
Cover clothes, footwear, toiletries, documents, electronics, health and accessories, matched to the weather, altitude,
coast and trip style. Names short (max 6 words). Reasons max 12 words. No brand names. For medicines say
"Your regular medicines" -- never name a drug."""


def ai_suggestions(f: TripFacts) -> list[Suggestion]:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    resp = client.models.generate_content(
        model=settings.LLM_MODEL,
        contents=_PROMPT.format(facts="\n".join(f"- {line}" for line in f.lines()), cats=list(CATEGORIES)),
        config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.4),
    )
    raw = json.loads(resp.text or "{}")
    out: list[Suggestion] = []
    for it in raw.get("items", [])[:60]:
        try:
            name = " ".join(str(it["name"]).split())[:80]
            cat = it.get("category") if it.get("category") in CATEGORIES else "other"
            qty = max(1, min(int(it.get("quantity", 1)), 99))
            if name:
                out.append(Suggestion(name=name, category=cat, quantity=qty, reason=str(it.get("reason", ""))[:120]))
        except (KeyError, TypeError, ValueError):
            continue
    if len(out) < 10:
        raise ValueError("Model returned too few usable items")
    return out


def suggest(db: Session, trip: Trip, user_id: uuid.UUID) -> Suggestions:
    """Suggestions not already on the person's list."""
    facts = trip_facts(db, trip)
    source = "rules"
    items: list[Suggestion]
    if settings.GEMINI_API_KEY:
        try:
            items, source = ai_suggestions(facts), "ai"
        except Exception:  # noqa: BLE001 -- fall back to the rules, never an error page
            logger.exception("AI packing suggestions failed; using the rules")
            items = rule_suggestions(facts)
    else:
        items = rule_suggestions(facts)
    have = {i.name.casefold() for i in _items(db, trip.id, user_id)}
    return Suggestions(
        items=[s for s in items if s.name.casefold() not in have],
        source=source,  # type: ignore[arg-type]
        context=facts.lines(),
    )


# ---------------------------------------------------------------- admin

def target_user(db: Session, email: str | None) -> User | None:
    if not email:
        return None
    user = db.scalar(select(User).where(User.email == email.lower()))
    if user is None:
        raise PackingError("No account with that email")
    return user
