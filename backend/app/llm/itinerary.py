"""Turn a trip request into a day-by-day plan.

One public function, `generate_itinerary`. It calls Gemini when GEMINI_API_KEY
is set and falls back to a deterministic local plan when it is not, so the app
is usable before anyone has an API key and the test suite never touches the
network.

Phase 2 replaces the body of `_build_prompt` with the RAG version; the signature
and the return type stay as they are.
"""
from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

from app.core.config import settings
from app.llm.prompts import (
    GOVT_CONTEXT_TEMPLATE,
    ITINERARY_PROMPT,
    ITINERARY_SYSTEM,
    MEMORY_CONTEXT_TEMPLATE,
    THINKING_CONTEXT_TEMPLATE,
)

logger = logging.getLogger(__name__)

MAX_DAYS = 30


@dataclass
class GeneratedItinerary:
    day_plan: list[dict[str, Any]]
    budget_breakdown: dict[str, float]
    explanation: str
    # False when the plan came from the local fallback rather than the model.
    from_model: bool = True
    warnings: list[str] = field(default_factory=list)
    # How it went: model calls made (a retry after a failed check counts),
    # tokens used and time taken. Zero for the local fallback.
    attempts: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: float = 0.0


class ItineraryGenerationError(Exception):
    pass


def generate_itinerary(
    *,
    destination: str,
    start_date: date,
    end_date: date,
    budget: float,
    travelers: int,
    style_tags: list[str],
    memory_context: str | None = None,
    govt_context: str | None = None,
    group_context: str | None = None,
    thinking_context: str | None = None,
) -> GeneratedItinerary:
    days = (end_date - start_date).days + 1
    if days < 1:
        raise ItineraryGenerationError("End date must not be before the start date")
    if days > MAX_DAYS:
        raise ItineraryGenerationError(f"Trips longer than {MAX_DAYS} days are not supported")

    if not settings.GEMINI_API_KEY:
        return _fallback_plan(
            destination=destination, start_date=start_date, days=days,
            budget=budget, style_tags=style_tags,
        )

    prompt = _build_prompt(
        destination=clean_field(destination, 120), start_date=start_date, end_date=end_date,
        days=days, budget=budget, travelers=travelers, style_tags=style_tags,
        memory_context=memory_context, govt_context=govt_context,
        group_context=group_context, thinking_context=thinking_context,
    )

    # Guardrail: every answer is checked against the request. One retry with
    # the problems spelled out, then the local outline -- never a broken plan.
    used = {"attempts": 0, "tokens_in": 0, "tokens_out": 0, "latency_ms": 0.0}
    problems: list[str] = []
    ask = prompt
    for attempt in range(MAX_ATTEMPTS):
        try:
            raw, usage = _call_gemini_measured(ask)
            for k in ("tokens_in", "tokens_out", "latency_ms"):
                used[k] += usage[k]
            used["attempts"] = attempt + 1
            plan, problems = check_plan(_parse_json(raw), start_date=start_date, days=days, budget=budget)
        except Exception as exc:  # noqa: BLE001 -- a bad plan must not 500 the request
            plan, problems = None, [str(exc)]
            used["attempts"] = attempt + 1
        if plan is not None and not problems:
            for k, v in used.items():
                setattr(plan, k, v)
            if attempt:
                plan.warnings.append("The first draft failed a check and was redone.")
            return plan
        logger.warning("Itinerary attempt %d failed checks: %s", attempt + 1, "; ".join(problems))
        ask = prompt + RETRY_NOTE.format(problems="\n".join(f"- {p}" for p in problems[:8]))

    plan = _fallback_plan(
        destination=destination, start_date=start_date, days=days,
        budget=budget, style_tags=style_tags,
    )
    plan.warnings.append("The planner's answers did not pass our checks, so this is an outline only.")
    for k, v in used.items():
        setattr(plan, k, v)
    return plan


MAX_ATTEMPTS = 2
MAX_ITEMS_PER_DAY = 8
BUDGET_SLACK = 1.02  # rounding in the model's sums is fine; overspending is not
RETRY_NOTE = (
    "\n\nYour previous answer failed these checks:\n{problems}\n"
    "Return the corrected JSON only, in exactly the shape asked for."
)
_TIME = re.compile(r"^([01]?\d|2[0-3]):[0-5]\d$")


def clean_field(text: str, limit: int) -> str:
    """Free text from the traveller goes into the prompt as data. Strip what
    could make it read as structure or instructions -- line breaks, braces,
    backticks, quotes -- and cap the length. (Prompt-injection guardrail;
    the system prompt also says to treat these fields as data.)"""
    text = re.sub(r"[\x00-\x1f`{}<>\[\]\"\\]", " ", text or "")
    return re.sub(r"\s+", " ", text).strip()[:limit]


def _num(v: Any) -> float | None:
    try:
        n = float(v)
    except (TypeError, ValueError):
        return None
    return n if n >= 0 and n == n else None


def check_plan(data: Any, *, start_date: date, days: int, budget: float) -> tuple[GeneratedItinerary | None, list[str]]:
    """Validate a model answer against the request. Small slips are repaired
    (day numbers, dates, a missing cost); real problems are returned as a list
    of sentences the model can act on."""
    problems: list[str] = []
    if not isinstance(data, dict):
        return None, ["The answer was not a JSON object."]
    day_plan = data.get("day_plan")
    breakdown = data.get("budget_breakdown")
    if not isinstance(day_plan, list) or not day_plan:
        return None, ["day_plan is missing or empty."]
    if len(day_plan) != days:
        problems.append(f"day_plan has {len(day_plan)} days; the trip has {days}.")

    clean_days = []
    for i, day in enumerate(day_plan[:days]):
        items = day.get("items") if isinstance(day, dict) else None
        if not isinstance(items, list) or not items:
            problems.append(f"Day {i + 1} has no items.")
            items = []
        if len(items) > MAX_ITEMS_PER_DAY:
            problems.append(f"Day {i + 1} has {len(items)} items; use at most {MAX_ITEMS_PER_DAY}.")
        rows = []
        for it in items[:MAX_ITEMS_PER_DAY]:
            if not isinstance(it, dict) or not str(it.get("activity") or "").strip():
                problems.append(f"Day {i + 1} has an item without an activity.")
                continue
            time_ = str(it.get("time") or "").strip()
            rows.append({
                "time": time_ if _TIME.match(time_) else "",
                "place": str(it.get("place") or "").strip()[:200],
                "activity": str(it["activity"]).strip()[:300],
                "estimated_cost": _num(it.get("estimated_cost")) or 0.0,
            })
        clean_days.append({"day": i + 1, "date": (start_date + timedelta(days=i)).isoformat(), "items": rows})

    if not isinstance(breakdown, dict) or not breakdown:
        problems.append("budget_breakdown is missing.")
        clean_breakdown: dict[str, float] = {}
    else:
        clean_breakdown = {}
        for k, v in breakdown.items():
            n = _num(v)
            if n is None:
                problems.append(f"budget_breakdown['{k}'] is not a non-negative number.")
            else:
                clean_breakdown[str(k)] = n
        total = sum(clean_breakdown.values())
        if total > budget * BUDGET_SLACK:
            problems.append(f"budget_breakdown adds up to INR {total:,.0f}, over the INR {budget:,.0f} budget.")

    if problems:
        return None, problems
    return GeneratedItinerary(
        day_plan=clean_days, budget_breakdown=clean_breakdown,
        explanation=str(data.get("explanation") or "")[:1000],
    ), []


def _build_prompt(
    *, destination: str, start_date: date, end_date: date, days: int,
    budget: float, travelers: int, style_tags: list[str], memory_context: str | None,
    govt_context: str | None = None,
    group_context: str | None = None,
    thinking_context: str | None = None,
) -> str:
    context = (
        MEMORY_CONTEXT_TEMPLATE.format(memory=memory_context) if memory_context else ""
    )
    govt = GOVT_CONTEXT_TEMPLATE.format(facts=govt_context) if govt_context else ""
    return ITINERARY_PROMPT.format(
        days=days,
        destination=destination,
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
        travelers=travelers,
        budget=f"{budget:,.0f}",
        style_tags=", ".join(style_tags) if style_tags else "no particular preference",
        retrieved_context=context,
        govt_context=govt,
        group_context=f"{group_context}\n" if group_context else "",
        thinking_context=(
            THINKING_CONTEXT_TEMPLATE.format(notes=thinking_context) if thinking_context else ""
        ),
    )


def _call_gemini_measured(prompt: str) -> tuple[str, dict]:
    """One model call, with the tokens it used and how long it took."""
    t0 = time.perf_counter()
    response = _gemini_response(prompt)
    if not response.text:
        raise ItineraryGenerationError("Empty response from the model")
    meta = getattr(response, "usage_metadata", None)
    tokens_in = int(getattr(meta, "prompt_token_count", 0) or 0)
    # Thinking tokens are billed as output.
    tokens_out = int(getattr(meta, "candidates_token_count", 0) or 0) + int(getattr(meta, "thoughts_token_count", 0) or 0)
    return response.text, {"tokens_in": tokens_in, "tokens_out": tokens_out,
                           "latency_ms": (time.perf_counter() - t0) * 1000}


def _call_gemini(prompt: str) -> str:
    return _call_gemini_measured(prompt)[0]


def _gemini_response(prompt: str):
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    response = client.models.generate_content(
        model=settings.LLM_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=ITINERARY_SYSTEM,
            response_mime_type="application/json",
            temperature=0.7,
        ),
    )
    return response


def _parse_json(raw: str) -> Any:
    """Models sometimes wrap JSON in fences despite being told not to."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0]
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ItineraryGenerationError(f"The answer was not valid JSON ({exc.msg}).") from exc


def _parse_response(raw: str) -> GeneratedItinerary:
    """Models sometimes wrap JSON in fences despite being told not to."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0]

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ItineraryGenerationError(f"Model did not return JSON: {exc}") from exc

    day_plan = data.get("day_plan")
    breakdown = data.get("budget_breakdown")
    if not isinstance(day_plan, list) or not day_plan:
        raise ItineraryGenerationError("Response has no day_plan")
    if not isinstance(breakdown, dict):
        raise ItineraryGenerationError("Response has no budget_breakdown")

    return GeneratedItinerary(
        day_plan=day_plan,
        budget_breakdown={k: float(v) for k, v in breakdown.items()},
        explanation=str(data.get("explanation") or ""),
    )


def _fallback_plan(
    *, destination: str, start_date: date, days: int, budget: float, style_tags: list[str],
) -> GeneratedItinerary:
    """A plain skeleton so the trip flow works with no API key and no network.

    It is deliberately obvious rather than fake-detailed -- a made-up itinerary
    that looks real would be worse than one that says it is an outline.
    """
    per_day = budget / days if days else budget

    day_plan = [
        {
            "day": n + 1,
            "date": (start_date + timedelta(days=n)).isoformat(),
            "items": [
                {"time": "09:00", "place": destination,
                 "activity": "Morning: explore the main sights",
                 "estimated_cost": round(per_day * 0.2)},
                {"time": "13:00", "place": destination,
                 "activity": "Lunch and a local market walk",
                 "estimated_cost": round(per_day * 0.15)},
                {"time": "16:00", "place": destination,
                 "activity": "Afternoon: a stop matching your interests",
                 "estimated_cost": round(per_day * 0.15)},
            ],
        }
        for n in range(days)
    ]

    return GeneratedItinerary(
        day_plan=day_plan,
        budget_breakdown={
            "stay": round(budget * 0.40),
            "food": round(budget * 0.25),
            "travel": round(budget * 0.25),
            "misc": round(budget * 0.10),
        },
        explanation=(
            f"An outline for {days} day(s) in {destination}"
            + (f", leaning towards {', '.join(style_tags)}" if style_tags else "")
            + ". Add GEMINI_API_KEY to .env for a real day-by-day plan."
        ),
        from_model=False,
        warnings=["No GEMINI_API_KEY is set, so this is a placeholder outline."],
    )
