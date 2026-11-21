"""Read a travel question -- English or Hinglish -- into the facts the
recommender needs: budget, days, people, month, where from, and the mood.

Rules, not a model, so it works with no API key and is easy to test. When
GEMINI_API_KEY is set the reply is written by Gemini, but the numbers still
come from here and from the recommender.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

MONTHS = {
    "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3, "april": 4, "apr": 4,
    "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7, "august": 8, "aug": 8,
    "september": 9, "sept": 9, "sep": 9, "october": 10, "oct": 10, "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}

# mood word -> (trip styles, place filter)
MOODS: list[tuple[tuple[str, ...], str, tuple[str, ...], str | None]] = [
    (("pahad", "pahaad", "pahado", "pahadon", "pahar", "hill", "hills", "hill station", "mountain", "mountains",
      "snow", "baraf", "barf", "himalaya", "himalayas"), "mountains", ("nature", "adventure"), "hills"),
    (("beach", "beaches", "samundar", "samandar", "sea", "coast", "island", "islands"), "beach", ("relax",), "coast"),
    (("peaceful", "peace", "sukoon", "shanti", "calm", "relax", "relaxing", "chill", "quiet"), "peaceful", ("relax",), None),
    (("adventure", "trek", "trekking", "rafting", "paragliding", "thrill", "camping", "hike", "hiking"), "adventure", ("adventure",), None),
    (("temple", "temples", "mandir", "history", "historical", "heritage", "fort", "forts", "culture", "spiritual",
      "palace", "palaces"), "culture & heritage", ("culture",), None),
    (("food", "khana", "foodie", "street food", "cuisine"), "food", ("food",), None),
    (("jungle", "wildlife", "safari", "forest", "nature", "waterfall", "waterfalls", "greenery"), "nature", ("nature",), None),
    (("honeymoon", "romantic"), "romantic", ("relax", "nature"), None),
]

_UNIT_RE = r"(k|thousand|hazaa?r|hajar|hzr|lakhs?|lacs?|l)\b"

_WHERE = ("kahan", "kaha", "kidhar", "where", "suggest", "recommend", "ghum", "ghoom", "ghumne", "ghoomne",
          "jaun", "jau", "jaa sakta", "ja sakta", "ja sakte", "go", "trip", "travel", "getaway", "destination", "place")


@dataclass
class Query:
    text: str
    budget: float | None = None
    days: int | None = None
    travelers: int | None = None
    month: int | None = None
    origin: str | None = None
    moods: list[str] = field(default_factory=list)
    styles: list[str] = field(default_factory=list)
    want_hills: bool = False
    want_coast: bool = False
    asks_where: bool = False
    # "weekend" (Sat-Sun), "long_weekend" (Fri-Sun), "weekdays" (from Monday) or None
    when: str | None = None
    assumed: list[str] = field(default_factory=list)


def _num(s: str) -> float:
    return float(s.replace(",", ""))


def _scale(unit: str | None) -> int:
    if not unit:
        return 1
    return 100_000 if unit.startswith("l") else 1_000


def _budget(t: str) -> float | None:
    # "₹15,000", "rs 15k", "1.5 lakh", "15 hazar", "budget 20000", "20000 ka budget"
    m = re.search(r"(?:₹|\brs\.?|\binr|\brupees?)\s*([\d,]+(?:\.\d+)?)\s*(?:" + _UNIT_RE + ")?", t)
    if m:
        return _num(m.group(1)) * _scale(m.group(2))
    m = re.search(r"([\d,]+(?:\.\d+)?)\s*" + _UNIT_RE, t)
    if m:
        return _num(m.group(1)) * _scale(m.group(2))
    m = re.search(r"([\d,]{4,})\s*(?:rs|rupees|rupay|rupaye|ka budget|budget|tak)\b", t) or \
        re.search(r"budget\D{0,12}([\d,]{4,})", t)
    if m:
        return _num(m.group(1))
    return None


_WEEKDAYS = re.compile(r"\b(weekdays?|week days?|mon(day)?\s*(-|to|se)\s*fri(day)?|hafte ke beech|working days)\b")


def _when(t: str) -> str | None:
    if _WEEKDAYS.search(t):
        return "weekdays"
    if "long weekend" in t:
        return "long_weekend"
    if re.search(r"\b(weekend|weekends|saturday|sunday|sat-sun|shanivar|ravivar)\b", t):
        return "weekend"
    return None


def _days(t: str) -> int | None:
    m = re.search(r"(\d+)\s*(?:days?|din|dino|dinon|day trip)\b", t)
    if m:
        return int(m.group(1))
    m = re.search(r"(\d+)\s*(?:nights?|raat|raatein)\b", t)
    if m:
        return int(m.group(1)) + 1
    if "long weekend" in t:
        return 3
    if re.search(r"\bweekends?\b", t):
        return 2
    if _WEEKDAYS.search(t):
        return None
    if re.search(r"\b(a|one|ek)\s+(week|hafta|hafte)\b|\bweek\b|\bhafte?\b", t):
        return 7
    return None


def _travelers(t: str) -> int | None:
    m = re.search(r"family of (\d+)", t) or re.search(
        r"(\d+)\s*(?:people|persons?|log|logon|logo|travell?ers|friends|adults|members|jan|bande|dost)\b", t)
    if m:
        return int(m.group(1))
    if re.search(r"\b(couple|wife|husband|partner|gf|bf|girlfriend|boyfriend|biwi|honeymoon)\b", t):
        return 2
    if re.search(r"\b(solo|akela|akele|alone|myself|i alone)\b", t):
        return 1
    return None


def _month(t: str, today: date) -> int | None:
    if re.search(r"\b(next month|agle mahine|agla mahina)\b", t):
        return today.month % 12 + 1
    if re.search(r"\b(this month|is mahine|abhi|this week|is hafte|kal|tomorrow|this weekend)\b", t):
        return today.month
    for word, n in sorted(MONTHS.items(), key=lambda kv: -len(kv[0])):
        if re.search(rf"\b{word}\b", t):
            return n
    return None


def _origin(t: str) -> str | None:
    m = re.search(r"\bfrom\s+([a-z][a-z .]{1,30}?)(?=\s+(?:to|for|in|with|under|on|budget|and)\b|[,.?!]|$)", t)
    if m:
        return m.group(1).strip().title()
    m = re.search(r"\b([a-z]{3,}(?:\s[a-z]{3,})?)\s+se\b", t)
    if m and m.group(1).split()[-1] not in ("mujhe", "humein", "hum", "main", "kahan", "kaha", "yahan", "ghar"):
        return m.group(1).split()[-1].title()
    return None


def parse(text: str, today: date | None = None) -> Query:
    today = today or date.today()
    t = " " + " ".join(text.lower().split()) + " "
    q = Query(text=text)
    q.budget = _budget(t)
    q.days = _days(t)
    q.travelers = _travelers(t)
    q.month = _month(t, today)
    q.origin = _origin(t)
    q.when = _when(t)
    styles: list[str] = []
    for words, label, s, place in MOODS:
        if any(re.search(rf"\b{re.escape(w)}\b", t) for w in words):
            q.moods.append(label)
            styles.extend(s)
            q.want_hills |= place == "hills"
            q.want_coast |= place == "coast"
    q.styles = list(dict.fromkeys(styles))
    q.asks_where = bool(q.budget or q.moods) or any(re.search(rf"\b{w}\b", t) for w in _WHERE)
    return q
