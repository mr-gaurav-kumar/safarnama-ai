"""The travel assistant: answer "where can I go on ₹15k for 3 days?" and
"how is Manali in January?" with real places, a tentative budget and the
weather.

  1. parse.py reads budget, days, people, month, where from and mood.
  2. Where-to-go questions go to the Budget Recommender (style x budget x
     season); a named place is looked up directly.
  3. estimate.py prices each pick from where the person starts; weather.py
     adds the season (model) and, for trips this month, a live forecast.
  4. Gemini writes the reply from those facts when GEMINI_API_KEY is set,
     told to use only these numbers; otherwise a template does.

Every number shown comes from steps 1-3, never from the language model.
"""
from __future__ import annotations

import difflib
import json
import logging
import re
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.assistant import estimate as est
from app.assistant import weather
from app.assistant.parse import MONTHS as _PARSE_MONTHS
from app.assistant.parse import MOODS as _PARSE_MOODS
from app.assistant.parse import Query, parse
from app.core.config import settings
from app.ml.budget_recommender import recommend
from app.ml.features import all_destinations, match
from app.models.destination import DestinationFeature
from app.models.user import User
from app.schemas.assistant import AssistantReply, ChatTurn, Pick, Understood

logger = logging.getLogger(__name__)


def parse_months() -> list[str]:
    return list(_PARSE_MONTHS)

MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
               "October", "November", "December"]
HINGLISH = re.compile(r"\b(hai|hain|mein|mai|kahan|kaha|ghum|ghoom|din|log|kya|mujhe|hum|kaisa|kitna|chahiye|jaana|jana|se|ka|ki|ke)\b")
MAX_PICKS = 4
SEASON_HI = {
    "ideal": "ghoomne ka sabse accha time hai",
    "pleasant": "mausam suhana rehta hai",
    "hot": "kaafi garmi rehti hai",
    "rainy": "monsoon ka time hai, baarish zyada hoti hai",
    "cold": "kaafi thand hoti hai, barf aur band raaste ho sakte hain",
}
NO_BUDGET = 10_000_000.0


def _origin_point(db: Session, rows: list[DestinationFeature], name: str | None) -> tuple[tuple[float, float] | None, str | None]:
    if not name:
        return None, None
    city = name.split(",")[0].strip()
    row = match(rows, city)
    if row is not None:
        return (row.lat, row.lng), row.name
    if city.lower() in est.ORIGINS:
        return est.ORIGINS[city.lower()], city.title()
    try:
        from app.geo.geocode import geocode

        p = geocode(city)
        if p is not None:
            return (p.lat, p.lng), city.title()
    except Exception:  # noqa: BLE001 -- unknown origin just means no travel estimate
        logger.info("Could not place origin %s", city)
    return None, city.title()


# Words that look like places but never are -- so "for the weekend" or
# "in december" is not read as a place.
_NOT_PLACES = {
    "the", "a", "an", "me", "us", "my", "our", "family", "friends", "couple", "trip", "budget", "weekend", "week",
    "days", "day", "night", "nights", "people", "person", "travel", "holiday", "vacation", "honeymoon", "india",
    "mountains", "hills", "beach", "beaches", "snow", "summer", "winter", "monsoon", "next", "this", "month",
    "somewhere", "place", "places", "kahin", "kuch", "ghoomne", "ghumne", "jaana", "jana", "plan", "cost", "price",
    "mera", "meri", "apna", "sabse", "kitna", "kitne", "kharcha", "ghar", "sasta", "accha", "achha", "best",
    "cheap", "good", "nice", "family", "kids", "parents", "office", "college", "group",
    *parse_months(), *(w for words, *_ in _PARSE_MOODS for w in words),
}


def _phrases(text: str) -> list[str]:
    words = re.findall(r"[a-z]+", text.lower())
    out = [" ".join(words[i:i + 2]) for i in range(len(words) - 1)]
    return out + [w for w in words if len(w) >= 4]


def find_place(rows: list[DestinationFeature], text: str) -> DestinationFeature | None:
    """The destination named in the text -- exact name or alias first, then a
    near spelling ("nanital" -> Nainital, "dharmshala" -> Dharamshala)."""
    exact = match(rows, text)
    if exact is not None:
        return exact
    names: dict[str, DestinationFeature] = {}
    for r in rows:
        for n in (r.name, *(r.aliases or [])):
            names[n.lower()] = r
    for phrase in _phrases(text):
        if phrase in _NOT_PLACES:
            continue
        hit = difflib.get_close_matches(phrase, list(names), n=1, cutoff=0.8)
        if hit and abs(len(hit[0]) - len(phrase)) <= 3:
            return names[hit[0]]
    return None


_ASKED_PLACE = re.compile(
    r"\b(?:for|to|of|visit|about|in)\s+(?:the\s+)?([a-z]{4,}(?:\s[a-z]{4,})?)\s*(?:trip|ka|ki|ke|$|[?.!,])"
    r"|\b([a-z]{4,})\s+(?:ka|ki|ke|jaana|jana|ghumna|ghoomna|trip)\b"
)


def unknown_place(text: str) -> str | None:
    """A place the person clearly asked about, that isn't in our list."""
    for m in _ASKED_PLACE.finditer(text.lower().strip()):
        name = (m.group(1) or m.group(2) or "").strip()
        if name and name.split()[-1] not in _NOT_PLACES and name not in _NOT_PLACES:
            return name.title()
    return None


def _start_date(month: int, today: date, when: str | None = None) -> date:
    """The first sensible start date in that month: a week out for this
    month, the 1st otherwise -- moved to the next Saturday for a weekend,
    Friday for a long weekend, Monday for weekdays."""
    if month == today.month:
        base = today + timedelta(days=1 if when else 7)
    else:
        base = date(today.year if month > today.month else today.year + 1, month, 1)
    target = {"weekend": 5, "long_weekend": 4, "weekdays": 0}.get(when or "")
    if target is None:
        return base
    return base + timedelta(days=(target - base.weekday()) % 7)


def _pick(
    row: DestinationFeature, q: Query, *, days: int, travelers: int, month: int, origin: tuple[float, float] | None,
    reasons: list[str], today: date, live: bool,
) -> Pick:
    start = _start_date(month, today, q.when)
    e = est.estimate(
        daily_cost=row.daily_cost, days=days, travelers=travelers, budget=q.budget,
        origin=origin, dest=(row.lat, row.lng), name=row.name, start=start,
    )
    s = weather.season_for(row.lat, row.lng, row.altitude_m, row.coastal, month)
    return Pick(
        name=row.name, state=row.state, blurb=row.blurb or "", reasons=reasons[:3],
        season=s, live=weather.live_forecast(row.lat, row.lng) if live else None,
        estimate=e.__dict__, altitude_m=row.altitude_m, coastal=row.coastal,
        plan={
            "destination": f"{row.name}, {row.state}", "days": days, "travelers": travelers,
            "budget": int(q.budget or e.total), "tags": ",".join(q.styles), "start": start.isoformat(),
        },
    )


def _template(q: Query, u: Understood, picks: list[Pick], intent: str, hinglish: bool, missing: str | None = None) -> str:
    money = lambda n: f"₹{n:,.0f}"  # noqa: E731
    if intent == "unknown":
        return (
            f"{missing} abhi meri list mein nahi hai, isliye uska kharcha aur mausam main pakka nahi bata sakta. "
            "Paas ki koi badi jagah ka naam likhiye, ya “pahad, 3 din, ₹20,000” jaisa poochiye."
            if hinglish else
            f"I don't have {missing} in my list yet, so I can't give its budget or weather reliably. Try a nearby "
            "well-known place, or ask like “hills, 3 days, ₹20,000”."
        )
    if intent == "help":
        return (
            "Main aapki trip plan karne mein help kar sakta hoon. Aise poochiye: “₹15,000 mein 3 din, Delhi se, "
            "pahad” ya “Goa December mein kaisa rahega?”"
            if hinglish else
            "I can suggest where to go and what it will cost. Try: “₹15,000 for 3 days from Delhi, somewhere "
            "in the hills” or “How is Goa in December?”"
        )
    if not picks:
        return (
            f"{money(q.budget or 0)} mein {u.days} din ke liye koi jagah fit nahi ho rahi. Budget thoda badhaiye "
            "ya din kam kijiye." if hinglish else
            f"Nothing fits {money(q.budget or 0)} for {u.days} days. Try a bigger budget or fewer days."
        )
    month = u.month_name or ""
    if intent == "place":
        p = picks[0]
        e = p.estimate
        line = (f"{p.name} mein {month} mein {SEASON_HI.get(p.season['label'], p.season['text'])}. {u.days} din, {u.travelers} log: "
                f"lagbhag {money(e['total'])}" if hinglish else
                f"{p.name} in {month} is {p.season['text']}. For {u.days} days and {u.travelers} "
                f"{'person' if u.travelers == 1 else 'people'}, expect roughly {money(e['total'])}")
        if e.get("verdict") in ("tight", "over"):
            line += " — budget se thoda upar hai" if hinglish else " — a bit above your budget"
        line += "."
        if e.get("weekend_nights"):
            n = e["weekend_nights"]
            line += (f" Isme {n} weekend raat hai, jab hotel ~25% mehenge hote hain." if hinglish
                     else f" That includes {n} weekend night{'s' if n > 1 else ''}, when stays cost about 25% more.")
        return line
    names = ", ".join(p.name for p in picks)
    head = (f"{u.days} din, {u.travelers} log" + (f", {money(q.budget)}" if q.budget else "") + f" — {month} ke liye ye jagahein sahi rahengi: {names}."
            if hinglish else
            f"For {u.days} days, {u.travelers} {'person' if u.travelers == 1 else 'people'}"
            + (f" and {money(q.budget)}" if q.budget else "") + f" in {month}, these fit well: {names}.")
    if q.when in ("weekend", "long_weekend"):
        head += (" Weekend pe hotel lagbhag 25% mehenge aur bheed zyada hoti hai — Sunday–Monday ya weekdays mein jaoge toh sasta padega."
                 if hinglish else " Weekend nights cost about 25% more and places are busier — going Sunday to Monday or on weekdays is cheaper.")
    elif q.when == "weekdays":
        head += (" Weekdays mein hotel saste aur bheed kam hoti hai — accha choice hai."
                 if hinglish else " Weekdays are a good call: cheaper stays and fewer crowds.")
    if not u.origin:
        head += (" Aap kahan se nikal rahe hain, bataiye toh aane-jaane ka kharcha bhi jod doonga."
                 if hinglish else " Tell me where you're starting from and I'll add the travel cost.")
    return head


_SYSTEM = """You are the travel assistant inside Safarnama, a trip planner for travellers in India.
Reply in the same language and script as the user (Hinglish if they write Hinglish). Be warm, practical and brief
(under 120 words). FACTS holds what the app worked out. For prices, budgets and weather use ONLY the numbers in
FACTS -- never invent a price, temperature or fare. The app shows a card for each pick with its full budget and
weather, so don't repeat every number: say in a line or two why each pick suits them, and mention anything they
should know (season, budget tight, assumptions made). If the user asks a general travel question (food, what to
see, safety, packing), answer it from general knowledge, briefly. Never claim to have booked anything."""


def _llm(history: list[ChatTurn], message: str, facts: dict) -> str:
    from google import genai
    from google.genai import types

    turns = "\n".join(f"{t.role.upper()}: {t.text}" for t in history[-6:])
    prompt = f"FACTS:\n{json.dumps(facts, ensure_ascii=False, default=str)}\n\nCONVERSATION:\n{turns}\nUSER: {message}"
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    r = client.models.generate_content(
        model=settings.LLM_MODEL, contents=prompt,
        config=types.GenerateContentConfig(system_instruction=_SYSTEM, temperature=0.6),
    )
    if not r.text:
        raise ValueError("empty reply")
    return r.text.strip()


def chat(db: Session, user: User, message: str, history: list[ChatTurn], today: date | None = None) -> AssistantReply:
    today = today or date.today()
    # Earlier turns fill in what this one leaves out ("make it 5 days").
    q = parse(message, today)
    for t in reversed(history):
        if t.role != "user":
            continue
        prev = parse(t.text, today)
        q.budget = q.budget or prev.budget
        q.days = q.days or prev.days
        q.travelers = q.travelers or prev.travelers
        q.month = q.month or prev.month
        q.origin = q.origin or prev.origin
        q.when = q.when or prev.when
        if not q.moods and prev.moods:
            q.moods, q.styles, q.want_hills, q.want_coast = prev.moods, prev.styles, prev.want_hills, prev.want_coast
        q.asks_where = q.asks_where or prev.asks_where

    rows = all_destinations(db)
    origin_name = q.origin or (user.home_town or None)
    origin, origin_label = _origin_point(db, rows, origin_name)

    assumed: list[str] = []
    days = q.days or 3
    if not q.days:
        assumed.append("3 days")
    travelers = q.travelers or 1
    if not q.travelers:
        assumed.append("1 traveller")
    month = q.month or (today.month if today.day <= 20 else today.month % 12 + 1)
    if not q.month:
        assumed.append(MONTH_NAMES[month - 1])
    live = month == today.month

    # A place named in the question -- but not the city they start from.
    text_wo_origin = re.sub(rf"\b{re.escape(q.origin)}\b", " ", message, flags=re.I) if q.origin else message
    named = find_place(rows, text_wo_origin)
    missing = None if named is not None else unknown_place(text_wo_origin)

    picks: list[Pick] = []
    if named is not None:
        intent = "place"
        picks = [_pick(named, q, days=days, travelers=travelers, month=month, origin=origin,
                       reasons=[named.blurb] if named.blurb else [], today=today, live=live)]
    elif missing is not None:
        intent = "unknown"
    elif q.asks_where:
        intent = "recommend"
        result = recommend(db, budget=q.budget or NO_BUDGET, days=days, travelers=travelers,
                           style_tags=q.styles, month=month, user_id=user.id, limit=20)
        by_name = {r.name: r for r in rows}
        fitting: list[Pick] = []
        over: list[Pick] = []
        for item in result["items"]:
            row = by_name.get(item["name"])
            if row is None or (q.want_hills and row.altitude_m < 1000) or (q.want_coast and not row.coastal):
                continue
            if origin is not None and est.distance_km(origin, (row.lat, row.lng)) < 40:
                continue  # not a trip from your own city
            if row.altitude_m >= 3000 and weather.season_for(row.lat, row.lng, row.altitude_m, row.coastal, month)["label"] == "cold":
                continue  # high passes in deep winter: roads often shut -- only if they ask by name
            # The recommender's own per-day budget line uses a flat travel
            # share; the card's estimate (with real distance) replaces it.
            reasons = [r for r in item["reasons"] if "/person/day" not in r and "per person per day" not in r]
            p = _pick(row, q, days=days, travelers=travelers, month=month, origin=origin,
                      reasons=reasons or ([row.blurb] if row.blurb else []), today=today, live=False)
            (over if p.estimate["verdict"] == "over" else fitting).append(p)
            if len(fitting) >= MAX_PICKS:
                break
        picks = fitting or over[:2]
        if live:
            for p in picks:
                row = by_name[p.name]
                p.live = weather.live_forecast(row.lat, row.lng)
    else:
        intent = "help"

    u = Understood(
        budget=int(q.budget) if q.budget else None, days=days, travelers=travelers, month=month,
        month_name=MONTH_NAMES[month - 1], origin=origin_label, moods=q.moods, assumed=assumed, when=q.when,
    )
    hinglish = bool(HINGLISH.search(message.lower()))
    reply, from_model = _template(q, u, picks, intent, hinglish, missing), False
    if settings.GEMINI_API_KEY:
        try:
            facts = {"understood": u.model_dump(), "intent": intent,
                     "picks": [p.model_dump(exclude={"plan"}) for p in picks],
                     "note": "Budgets are rough estimates: travel by likely mode + typical daily costs."}
            reply, from_model = _llm(history, message, facts), True
        except Exception:  # noqa: BLE001 -- the template reply is always there
            logger.exception("Assistant model call failed; using the template")
    return AssistantReply(reply=reply, intent=intent, understood=u, picks=picks, from_model=from_model)
