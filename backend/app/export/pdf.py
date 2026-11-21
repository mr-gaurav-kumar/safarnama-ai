"""Render a trip as a Safarnama PDF: the plan, how you are getting there, what
to pack, and a good-luck note that is different on every download.

Fonts are bundled TTFs (Fira Sans for text, Instrument Serif for headings), so
the rupee sign and most Latin text print as written. Model output can still
contain anything -- Devanagari, emoji -- so every string goes through _clean,
which keeps what the font can draw, swaps a few common symbols and replaces the
rest. An odd character can never turn an export into a 500.
"""
from __future__ import annotations

import logging
import math
import re
import unicodedata
import uuid
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

from fpdf import FPDF

from app.export.wishes import wish_for
from app.models.trip import Trip

logger = logging.getLogger(__name__)

HERE = Path(__file__).parent
FONTS = HERE / "fonts"
LOGO = HERE / "assets" / "logo_full.png"
TAGLINE = "Your Next Adventure, Perfectly Planned."

INDIGO = (28, 36, 82)
MARIGOLD = (242, 169, 59)
CREAM = (251, 244, 230)
INK = (27, 31, 42)
MUTED = (91, 95, 106)
SOFT = (176, 182, 206)  # muted text on the indigo band
RULE = (220, 218, 211)
PANEL = (247, 246, 242)
WISH_BG = (253, 244, 227)
TEAL = (16, 140, 152)  # from the logo

LEFT = 16
WIDTH = 178  # A4 210 mm minus 16 mm margins

MODE_LABEL = {"train": "Train", "flight": "Flight", "bus": "Bus", "hotel": "Stay", "other": "Travel"}
CATEGORY_LABEL = {
    "documents": "Documents", "clothes": "Clothes", "footwear": "Footwear", "toiletries": "Toiletries",
    "health": "Health", "electronics": "Electronics", "accessories": "Accessories", "other": "Other",
}

_FALLBACK = {
    "–": "-", "—": "-", "‒": "-", "−": "-", "‘": "'", "’": "'", "“": '"', "”": '"',
    "…": "...", "•": "-", " ": " ", "₹": "Rs ", "→": "->", "×": "x", "·": "-",
}


@lru_cache(maxsize=4)
def _cmap(file: str) -> frozenset[int]:
    from fontTools.ttLib import TTFont

    return frozenset(TTFont(FONTS / file).getBestCmap())


def _clean(text: Any, font: str = "FiraSans-Regular.ttf") -> str:
    s = unicodedata.normalize("NFKC", str(text if text is not None else ""))
    have = _cmap(font)
    out = []
    for ch in s:
        if ord(ch) in have or ch in "\n\t":
            out.append(ch)
        elif ch in _FALLBACK:
            out.append(_FALLBACK[ch] if all(ord(c) in have for c in _FALLBACK[ch]) else "?")
        elif unicodedata.category(ch) in ("So", "Sk", "Mn", "Cf", "Cs", "Co"):
            continue  # emoji, joiners and variation selectors: drop quietly
        else:
            out.append("?")
    return re.sub(r" {2,}", " ", "".join(out)).strip()


def _inr(value: Any) -> str:
    """₹1,25,000 -- Indian digit grouping."""
    try:
        n = round(float(value))
    except (TypeError, ValueError):
        return "-"
    sign, n = ("-" if n < 0 else ""), abs(n)
    s = str(n)
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        head = ",".join(re.findall(r"\d{1,2}", head[::-1]))[::-1]
        s = f"{head},{tail}"
    return f"{sign}₹{s}"


def _day(d: date | str | None, fmt: str = "%d %b %Y") -> str:
    if not d:
        return ""
    if isinstance(d, str):
        d = date.fromisoformat(d[:10])
    return d.strftime(fmt)


def _pref(label: str, value: str) -> str:
    """"Seat 14" but not "Room Room 3" when the traveller already wrote the word."""
    return value if value.lower().startswith(label.lower()) else f"{label} {value}"


def _when(t: datetime | None) -> str:
    return t.strftime("%d %b, %H:%M") if t else ""


def filename_for(trip: Trip) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", trip.destination.lower()).strip("-") or "trip"
    return f"{slug}-{trip.start_date.isoformat()}.pdf"


class _Doc(FPDF):
    def __init__(self, destination: str) -> None:
        super().__init__(format="A4")
        self.destination = destination
        self.add_font("Fira", "", FONTS / "FiraSans-Regular.ttf")
        self.add_font("Fira", "B", FONTS / "FiraSans-SemiBold.ttf")
        self.add_font("Fira", "I", FONTS / "FiraSans-Italic.ttf")
        self.add_font("Serif", "", FONTS / "InstrumentSerif-Regular.ttf")
        self.add_font("Serif", "I", FONTS / "InstrumentSerif-Italic.ttf")
        self.set_margins(LEFT, 18, LEFT)
        self.set_auto_page_break(auto=True, margin=20)

    def header(self) -> None:
        if self.page_no() == 1:
            if LOGO.exists():
                self.image(str(LOGO), x=LEFT, y=7, h=24)
            self.set_text_color(*INDIGO)
            self.set_font("Serif", "", 30)
            self.set_xy(LEFT + 41, 9)
            self.cell(90, 12, "Safarnama")
            self.set_text_color(*TEAL)
            self.set_font("Fira", "I", 10)
            self.set_xy(LEFT + 41.5, 21.5)
            self.cell(90, 5, TAGLINE)
            self.set_text_color(*INK)
            self.set_font("Fira", "B", 9.5)
            self.set_xy(110, 12)
            self.cell(84, 5, "Your trip plan", align="R")
            self.set_text_color(*MUTED)
            self.set_font("Fira", "", 8.5)
            self.set_xy(110, 17.5)
            self.cell(84, 5, f"Made on {date.today().strftime('%d %b %Y')}", align="R")
            self.set_draw_color(*MARIGOLD)
            self.set_line_width(0.8)
            self.line(LEFT, 35, LEFT + WIDTH, 35)
            self.set_line_width(0.2)
            self.set_y(42)
        else:
            if LOGO.exists():
                self.image(str(LOGO), x=LEFT, y=6.5, h=6.5)
            self.set_text_color(*MUTED)
            self.set_font("Fira", "", 8.5)
            self.set_xy(LEFT + 11.5, 7.2)
            self.cell(120, 5, _clean(f"Safarnama  -  {self.destination}"))
            self.set_y(18)

    def footer(self) -> None:
        self.set_y(-14)
        self.set_draw_color(*RULE)
        self.line(LEFT, self.get_y(), LEFT + WIDTH, self.get_y())
        self.set_font("Fira", "", 8)
        self.set_text_color(*MUTED)
        self.set_y(-12)
        self.cell(WIDTH / 2, 5, f"Safarnama  -  {TAGLINE}")
        self.cell(WIDTH / 2, 5, f"Page {self.page_no()}", align="R")


# ---------------------------------------------------------------- building blocks

def _room(pdf: FPDF, needed: float) -> None:
    if pdf.get_y() + needed > pdf.h - 22:
        pdf.add_page()


def _section(pdf: FPDF, title: str) -> None:
    _room(pdf, 30)
    pdf.ln(4)
    pdf.set_font("Serif", "", 19)
    pdf.set_text_color(*INDIGO)
    pdf.cell(0, 9, _clean(title, "InstrumentSerif-Regular.ttf"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(*RULE)
    pdf.line(LEFT, pdf.get_y() + 0.5, LEFT + WIDTH, pdf.get_y() + 0.5)
    pdf.ln(3.5)


def _text(pdf: FPDF, text: str, size: float = 10, style: str = "", color=INK, h: float = 5.2, x: float = LEFT,
          w: float = WIDTH) -> None:
    pdf.set_font("Fira", style, size)
    pdf.set_text_color(*color)
    pdf.set_x(x)
    pdf.multi_cell(w, h, _clean(text), new_x="LMARGIN", new_y="NEXT")


def _bullets(pdf: FPDF, lines: list[str]) -> None:
    for line in lines:
        _room(pdf, 8)
        y = pdf.get_y()
        pdf.set_fill_color(*MARIGOLD)
        pdf.ellipse(LEFT + 1, y + 2, 1.6, 1.6, style="F")
        _text(pdf, line, x=LEFT + 5, w=WIDTH - 5)
        pdf.ln(0.8)


# ---------------------------------------------------------------- sections

def _summary(pdf: FPDF, trip: Trip) -> None:
    pdf.set_font("Serif", "", 34)
    pdf.set_text_color(*INDIGO)
    pdf.multi_cell(WIDTH, 13, _clean(trip.destination, "InstrumentSerif-Regular.ttf"),
                   new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    days = (trip.end_date - trip.start_date).days + 1
    cells = [
        ("Dates", f"{_day(trip.start_date, '%d %b')} - {_day(trip.end_date)}"),
        ("Duration", f"{days} day{'s' if days != 1 else ''}"),
        ("Travellers", f"{trip.travelers} {'people' if trip.travelers != 1 else 'person'}"),
        ("Budget", _inr(trip.budget) if float(trip.budget) > 0 else "Not set"),
    ]
    gap, y = 3.0, pdf.get_y()
    w = (WIDTH - gap * 3) / 4
    for i, (label, value) in enumerate(cells):
        x = LEFT + i * (w + gap)
        pdf.set_fill_color(*PANEL)
        pdf.rect(x, y, w, 15, "F", round_corners=True, corner_radius=2)
        pdf.set_xy(x + 3.5, y + 2.6)
        pdf.set_font("Fira", "", 8)
        pdf.set_text_color(*MUTED)
        pdf.cell(w - 6, 4, label)
        pdf.set_xy(x + 3.5, y + 7.2)
        pdf.set_font("Fira", "B", 10.5)
        pdf.set_text_color(*INK)
        pdf.cell(w - 6, 5, _clean(value))
    pdf.set_y(y + 15 + 3)
    if trip.style_tags:
        _text(pdf, "Interests: " + ", ".join(t.capitalize() for t in trip.style_tags), size=9, color=MUTED)


def _wish(pdf: FPDF, trip: Trip, season: str | None) -> None:
    w = wish_for(trip.destination, season, list(trip.style_tags or []), trip.travelers)
    text = _clean(w.text, "InstrumentSerif-Italic.ttf")
    pdf.ln(4)
    pdf.set_font("Serif", "I", 15)
    inner = WIDTH - 16
    lines = pdf.multi_cell(inner, 7, text, dry_run=True, output="LINES")
    h = len(lines) * 7 + 16
    _room(pdf, h + 4)
    y = pdf.get_y()
    pdf.set_fill_color(*WISH_BG)
    pdf.rect(LEFT, y, WIDTH, h, "F", round_corners=True, corner_radius=2.5)
    pdf.set_fill_color(*MARIGOLD)
    pdf.rect(LEFT, y, 1.8, h, "F")
    pdf.set_text_color(*INDIGO)
    pdf.set_xy(LEFT + 9, y + 5)
    pdf.multi_cell(inner, 7, text, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Fira", "", 9)
    pdf.set_text_color(*MUTED)
    pdf.set_x(LEFT + 9)
    pdf.cell(inner, 5, f"- {w.signature}")
    pdf.set_y(y + h + 2)


def planner_voice(thought: str) -> bool:
    """Lines where the AI planner says what it will do ("I'll lean on budget
    stays"). Right for a plan it writes; wrong on a plan the traveller wrote."""
    return bool(re.search(r"\bI(?:'ll| will| am going to)\b", thought))


def _season(pdf: FPDF, thinking: dict | None, source: str = "ai") -> None:
    if not thinking or not thinking.get("thoughts"):
        return
    lines = [str(t) for t in thinking["thoughts"] if source == "ai" or not planner_voice(str(t))]
    if not lines:
        return
    _section(pdf, "Season and weather")
    _bullets(pdf, lines[:5])


def _travel(pdf: FPDF, tickets: list, pnr_of) -> None:
    moves = [t for t in tickets if t.mode != "hotel"]
    stays = [t for t in tickets if t.mode == "hotel"]
    _section(pdf, "Getting there")
    if not moves:
        _text(pdf, "No train, flight or bus tickets are saved for this trip yet. Add them under Tickets on the "
                   "trip page and they will appear here, with times, seats and PNR.", color=MUTED)
    for t in moves:
        title = " ".join(x for x in (t.provider, t.number) if x) or MODE_LABEL.get(t.mode, "Travel")
        route = " → ".join(x for x in (t.from_place, t.to_place) if x)
        bits = []
        if t.depart_at:
            bits.append(f"Departs {_when(t.depart_at)}")
        if t.arrive_at:
            bits.append(f"Arrives {_when(t.arrive_at)}")
        if t.seat:
            bits.append(_pref("Seat", t.seat))
        if t.travel_class:
            bits.append(_pref("Class", t.travel_class))
        try:
            pnr = pnr_of(t)
        except Exception:  # noqa: BLE001 -- a key problem must not stop the export
            pnr = None
        if pnr:
            bits.append(f"PNR {pnr}")
        _ticket(pdf, MODE_LABEL.get(t.mode, "Travel"), title, route, "   |   ".join(bits), t.notes)
    if stays:
        _section(pdf, "Where you are staying")
        for t in stays:
            bits = []
            if t.depart_at:
                bits.append(f"Check-in {_when(t.depart_at)}")
            if t.arrive_at:
                bits.append(f"Check-out {_when(t.arrive_at)}")
            if t.seat:
                bits.append(_pref("Room", t.seat))
            if t.number:
                bits.append(_pref("Booking", t.number))
            _ticket(pdf, "Stay", t.provider or "Hotel", t.to_place or t.from_place or "", "   |   ".join(bits), t.notes)


def _ticket(pdf: FPDF, mode: str, title: str, route: str, details: str, notes: str | None) -> None:
    _room(pdf, 24)
    y = pdf.get_y()
    pdf.set_font("Fira", "B", 8.5)
    pdf.set_text_color(*INDIGO)
    pdf.set_fill_color(*CREAM)
    pdf.set_xy(LEFT, y + 0.5)
    pdf.cell(18, 6, mode, align="C", fill=True)
    x = LEFT + 22
    pdf.set_xy(x, y)
    _text(pdf, title, size=10.5, style="B", x=x, w=WIDTH - 22)
    if route:
        _text(pdf, route, x=x, w=WIDTH - 22)
    if details:
        _text(pdf, details, size=9, color=MUTED, x=x, w=WIDTH - 22, h=4.8)
    if notes:
        _text(pdf, notes, size=9, style="I", color=MUTED, x=x, w=WIDTH - 22, h=4.8)
    pdf.ln(3)


def _packing(pdf: FPDF, items: list[tuple[str, str, int]], suggested: bool) -> None:
    rows_needed = len({c for c, _, _ in items}) + len(items)
    whole = math.ceil(rows_needed / 2) * 6.2 + (12 if suggested else 0)
    _room(pdf, min(whole, pdf.h - 60) + 24)  # start on a fresh page rather than split a short list
    _section(pdf, "Packing checklist")
    if not items:
        _text(pdf, "Nothing on your packing list yet. Open Packing on the trip page to build one.", color=MUTED)
        return
    if suggested:
        _text(pdf, "Your list for this trip is empty, so here is what we suggest for the weather and the trip. "
                   "Make it your own on the Packing page.", size=9, color=MUTED)
        pdf.ln(1.5)
    order = list(CATEGORY_LABEL)
    rows: list[tuple[str, str]] = []
    for cat in sorted({c for c, _, _ in items}, key=lambda c: order.index(c) if c in order else 99):
        rows.append(("cat", CATEGORY_LABEL.get(cat, cat.capitalize())))
        for c, name, qty in items:
            if c == cat:
                rows.append(("item", f"{name} × {qty}" if qty > 1 else name))
    row_h, col_w = 6.2, WIDTH / 2
    while rows:
        fit = int((pdf.h - 22 - pdf.get_y()) // row_h)
        if fit < 3:
            pdf.add_page()
            continue
        chunk = rows[: fit * 2]
        rows = rows[len(chunk):]
        per_col = fit if rows else math.ceil(len(chunk) / 2)
        if per_col < len(chunk) and chunk[per_col - 1][0] == "cat":
            # Never leave a heading at the foot of a column: pull its first
            # item up if there is room, otherwise push the heading across.
            per_col = per_col + 1 if per_col + 1 <= fit else per_col - 1
        y0 = pdf.get_y()
        for i, (kind, text) in enumerate(chunk):
            col, r = divmod(i, per_col)
            x, y = LEFT + col * col_w, y0 + r * row_h
            if kind == "cat":
                pdf.set_font("Fira", "B", 9)
                pdf.set_text_color(*INDIGO)
                pdf.set_xy(x, y + 0.8)
                pdf.cell(col_w - 4, 5, text)
            else:
                pdf.set_draw_color(*MUTED)
                pdf.set_line_width(0.3)
                pdf.rect(x + 0.5, y + 1.3, 3.4, 3.4, round_corners=True, corner_radius=0.6)
                pdf.set_font("Fira", "", 9.5)
                pdf.set_text_color(*INK)
                pdf.set_xy(x + 6, y + 0.8)
                pdf.cell(col_w - 10, 5, _clean(text))
        pdf.set_line_width(0.2)
        pdf.set_y(y0 + min(per_col, len(chunk)) * row_h + 2)
        if rows:
            pdf.add_page()


def _why(pdf: FPDF, it, source: str = "ai") -> None:
    if not it.explanation:
        return
    _section(pdf, "Why this plan" if source == "ai" else "Notes")
    _text(pdf, it.explanation)
    if it.memory_sources:
        shaped = ", ".join(f"{s.get('destination')} ({_day(s.get('start_date'))})" for s in it.memory_sources)
        pdf.ln(1)
        _text(pdf, f"Shaped by your past trips: {shaped}", size=9, color=MUTED)


def _budget(pdf: FPDF, trip: Trip, it) -> None:
    breakdown = it.budget_breakdown or {}
    if not breakdown:
        return
    _section(pdf, "Budget")
    total = 0.0
    for label, value in breakdown.items():
        _room(pdf, 8)
        pdf.set_font("Fira", "", 10)
        pdf.set_text_color(*INK)
        pdf.cell(WIDTH * 0.6, 6.5, _clean(str(label).replace("_", " ").capitalize()))
        pdf.cell(WIDTH * 0.4, 6.5, _inr(value), align="R", new_x="LMARGIN", new_y="NEXT")
        try:
            total += float(value)
        except (TypeError, ValueError):
            pass
    pdf.set_draw_color(*RULE)
    pdf.line(LEFT, pdf.get_y() + 0.5, LEFT + WIDTH, pdf.get_y() + 0.5)
    pdf.ln(1.5)
    pdf.set_font("Fira", "B", 10.5)
    pdf.cell(WIDTH * 0.6, 7, "Planned spend")
    pdf.cell(WIDTH * 0.4, 7, _inr(total), align="R", new_x="LMARGIN", new_y="NEXT")
    if float(trip.budget) <= 0:
        return
    pdf.set_font("Fira", "", 9.5)
    pdf.set_text_color(*MUTED)
    left = float(trip.budget) - total
    pdf.cell(WIDTH * 0.6, 6, f"Your budget {_inr(trip.budget)}")
    pdf.cell(WIDTH * 0.4, 6, f"{_inr(left)} to spare" if left >= 0 else f"{_inr(-left)} over", align="R",
             new_x="LMARGIN", new_y="NEXT")


TIME_W, COST_W = 16, 26


def _days(pdf: FPDF, it) -> None:
    if not it.day_plan:
        return
    _section(pdf, "Day by day")
    for day in it.day_plan:
        _room(pdf, 30)
        pdf.ln(1.5)
        y = pdf.get_y()
        pdf.set_fill_color(*PANEL)
        pdf.rect(LEFT, y, WIDTH, 8, "F", round_corners=True, corner_radius=1.5)
        pdf.set_xy(LEFT + 3, y + 1.4)
        pdf.set_font("Fira", "B", 10.5)
        pdf.set_text_color(*INDIGO)
        pdf.cell(20, 5.2, f"Day {day.get('day', '')}")
        pdf.set_font("Fira", "", 9.5)
        pdf.set_text_color(*MUTED)
        pdf.cell(80, 5.2, _day(day.get("date"), "%A, %d %b") if day.get("date") else "")
        pdf.set_y(y + 10)
        for item in day.get("items", []):
            _item_row(pdf, item)


def _item_row(pdf: FPDF, item: dict) -> None:
    _room(pdf, 14)
    y0 = pdf.get_y()
    text_w = WIDTH - TIME_W - COST_W
    pdf.set_font("Fira", "B", 9.5)
    pdf.set_text_color(*MARIGOLD)
    pdf.set_xy(LEFT, y0)
    pdf.cell(TIME_W, 5.5, _clean(item.get("time", "")))
    pdf.set_font("Fira", "", 9.5)
    pdf.set_text_color(*INK)
    pdf.set_xy(LEFT + TIME_W + text_w, y0)
    pdf.cell(COST_W, 5.5, _inr(item.get("estimated_cost")) if item.get("estimated_cost") else "", align="R")
    pdf.set_font("Fira", "B", 10)
    pdf.set_xy(LEFT + TIME_W, y0)
    pdf.multi_cell(text_w - 3, 5.5, _clean(item.get("activity", "")), new_x="LEFT", new_y="NEXT")
    if item.get("place"):
        pdf.set_font("Fira", "", 9)
        pdf.set_text_color(*MUTED)
        pdf.set_x(LEFT + TIME_W)
        pdf.multi_cell(text_w - 3, 4.8, _clean(item["place"]), new_x="LEFT", new_y="NEXT")
    pdf.set_x(LEFT)
    pdf.ln(2)


# ---------------------------------------------------------------- data

def _tickets(db, trip: Trip, user_id: uuid.UUID | None) -> list:
    from sqlalchemy import select

    from app.models.ticket import Ticket

    q = select(Ticket).where(Ticket.trip_id == trip.id, Ticket.user_id == (user_id or trip.user_id))
    return sorted(db.scalars(q), key=lambda t: (t.depart_at is None, t.depart_at or datetime.max))


def _packing_items(db, trip: Trip, user_id: uuid.UUID | None) -> tuple[list[tuple[str, str, int]], bool]:
    from sqlalchemy import select

    from app.models.packing import PackingItem
    from app.services import packing_service

    uid = user_id or trip.user_id
    mine = list(db.scalars(select(PackingItem).where(PackingItem.trip_id == trip.id, PackingItem.user_id == uid)
                           .order_by(PackingItem.created_at)))
    if mine:
        return [(i.category, i.name, i.quantity) for i in mine], False
    facts = packing_service.trip_facts(db, trip)
    return [(s.category, s.name, s.quantity) for s in packing_service.rule_suggestions(facts)], True


# ---------------------------------------------------------------- entry point

def render_itinerary_pdf(trip: Trip, db=None, user_id: uuid.UUID | None = None) -> bytes:
    """The whole plan as a PDF. With `db`, it also carries the requester's own
    tickets and packing list; without it, the plan alone."""
    if trip.itinerary is None:
        raise ValueError("This trip has no itinerary yet")
    it = trip.itinerary
    thinking = it.thinking or {}
    seasons = thinking.get("seasons") or []

    pdf = _Doc(trip.destination.split(",")[0].strip())
    pdf.add_page()
    _summary(pdf, trip)
    _wish(pdf, trip, seasons[0].get("label") if seasons else None)
    _season(pdf, thinking, getattr(trip, "source", "ai"))

    if db is not None:
        try:
            from app.services.tickets import pnr_of

            _travel(pdf, _tickets(db, trip, user_id), pnr_of)
        except Exception:  # noqa: BLE001 -- extras never stop the plan from exporting
            logger.exception("Could not add tickets to the PDF for trip %s", trip.id)
        try:
            items, suggested = _packing_items(db, trip, user_id)
            _packing(pdf, items, suggested)
        except Exception:  # noqa: BLE001
            logger.exception("Could not add the packing list to the PDF for trip %s", trip.id)

    _why(pdf, it, getattr(trip, "source", "ai"))
    _budget(pdf, trip, it)
    _days(pdf, it)
    return bytes(pdf.output())
