"""What a support message is about (intent) and how the person feels
(sentiment).

Without a Gemini key this is a small keyword classifier that understands
English and the Hinglish people actually type ("trip kab ready hoga"). With a
key, the reply call classifies too (see app/chat/reply.py), and this is the
fallback if that call fails.
"""
from __future__ import annotations

import re

INTENTS = (
    "greeting", "thanks", "status_check", "cancel_trip", "change_trip",
    "email_help", "export_help", "plan_help", "page_help", "other",
)
SENTIMENTS = ("positive", "neutral", "negative")

# Intents that describe a problem to solve. Asking about one of these again and
# again means the bot is not solving it -- that is what escalation looks for.
ACTIONABLE = frozenset({
    "status_check", "cancel_trip", "change_trip", "email_help", "export_help", "other",
})

# Checked in order; the first match wins, so specific intents come first.
_INTENT_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("cancel_trip", ("cancel", "delete my trip", "delete trip", "remove trip", "remove my trip",
                     "hata do", "hatao", "delete kar")),
    ("change_trip", ("change", "modify", "edit", "reschedule", "update my trip", "update trip",
                     "different dates", "badal", "shift my trip")),
    ("export_help", ("pdf", "download", "export", "print")),
    ("email_help", ("verify", "verification", "confirm my email", "confirmation email",
                    "no email", "didn't get", "didnt get", "not received", "email nahi",
                    "mail nahi", "email link", "reminder")),
    ("status_check", ("status", "where is my", "ready", "stuck", "processing", "loading",
                      "still planning", "taking long", "taking so long", "kab", "kitna time",
                      "not generated", "not showing", "itinerary not", "plan not")),
    ("plan_help", ("plan", "itinerary", "suggest", "recommend", "where should", "best time",
                   "visit", "go to", "trip to", "kahan", "ghumne", "budget for")),
    ("thanks", ("thank", "thanks", "thank you", "thx", "ty", "shukriya", "dhanyavad", "dhanyawad")),
    ("greeting", ("hi", "hello", "hey", "namaste", "hii", "good morning", "good evening")),
)

_NEGATIVE = (
    "angry", "frustrated", "frustrating", "annoyed", "annoying", "useless", "worst",
    "terrible", "awful", "horrible", "hate", "ridiculous", "pathetic", "disappointed",
    "disappointing", "waste", "broken", "rubbish", "garbage", "scam", "fed up",
    "bakwas", "bekar", "bekaar", "ghatiya", "faltu", "pagal", "wtf",
    "not working", "doesn't work", "doesnt work", "does not work", "not happy",
    "still not", "again and again", "no one", "nobody",
)
_POSITIVE = (
    "thanks", "thank you", "great", "awesome", "love", "perfect", "nice", "helpful",
    "amazing", "excellent", "cool", "badhiya", "mast", "zabardast", "shandaar",
)


def _has(text: str, phrase: str) -> bool:
    """Whole-word match, so 'hi' does not fire inside 'this'."""
    return re.search(rf"(?<![a-z]){re.escape(phrase)}(?![a-z])", text) is not None


def classify_intent(message: str) -> str:
    text = message.lower()
    for intent, phrases in _INTENT_PATTERNS:
        if any(_has(text, p) for p in phrases):
            return intent
    return "other"


def classify_sentiment(message: str) -> str:
    text = message.lower()
    negative = sum(_has(text, p) for p in _NEGATIVE)
    positive = sum(_has(text, p) for p in _POSITIVE)

    # Shouting is a signal on its own: three or more !!! or ???, or a message
    # that is mostly capitals.
    letters = [c for c in message if c.isalpha()]
    if re.search(r"[!?]{3,}", message):
        negative += 1
    if len(letters) >= 12 and sum(c.isupper() for c in letters) / len(letters) > 0.7:
        negative += 1

    if negative > positive:
        return "negative"
    if positive > negative:
        return "positive"
    return "neutral"


def classify(message: str) -> tuple[str, str]:
    return classify_intent(message), classify_sentiment(message)
