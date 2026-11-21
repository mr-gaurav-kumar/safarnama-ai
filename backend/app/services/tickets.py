"""My tickets: save, check and look up a traveller's own bookings.

Encryption, file checks and the private folder are the document vault's
(app/services/document_vault.py) -- one key, one set of rules.
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ticket import MODES, Ticket
from app.models.trip import Trip
from app.services import document_vault as vault

# How a booking reference looks for each kind of ticket.
PNR_RULES: dict[str, tuple[re.Pattern[str], str]] = {
    "train": (re.compile(r"\d{10}"), "A train PNR is 10 digits."),
    "flight": (re.compile(r"[A-Z0-9]{5,8}"), "A flight PNR / booking reference is 5–8 letters and numbers, like X7K2QA."),
    "bus": (re.compile(r"[A-Z0-9\-]{4,24}"), "Use the ticket or PNR number printed on the bus ticket."),
    "hotel": (re.compile(r"[A-Z0-9\-]{3,30}"), "Use the booking ID from the hotel confirmation."),
    "other": (re.compile(r"[A-Z0-9\-]{3,30}"), "Use letters and numbers only."),
}
TRAIN_NO = re.compile(r"\d{5}")
FLIGHT_NO = re.compile(r"[A-Z0-9]{2}\s?\d{1,4}[A-Z]?")
PNR_ENQUIRY = "https://www.indianrail.gov.in/enquiry/PNR/PnrEnquiry.html"


class TicketError(vault.VaultError):
    pass


class TicketNotFound(vault.DocumentNotFound):
    pass


@dataclass
class TicketInput:
    mode: str
    provider: str | None = None
    number: str | None = None
    pnr: str | None = None
    from_place: str | None = None
    to_place: str | None = None
    depart_at: datetime | None = None
    arrive_at: datetime | None = None
    seat: str | None = None
    travel_class: str | None = None
    passengers: int | None = None
    fare: float | None = None
    notes: str | None = None
    trip_id: uuid.UUID | None = None
    clear_trip: bool = False


def _text(v: str | None, n: int) -> str | None:
    if v is None:
        return None
    v = " ".join(v.split())
    return v[:n] or None


def clean_pnr(mode: str, raw: str | None) -> str | None:
    if raw is None or not raw.strip():
        return None
    p = re.sub(r"[\s/]", "", raw).upper()
    pattern, msg = PNR_RULES[mode]
    if not pattern.fullmatch(p):
        raise TicketError(msg)
    return p


def clean_number(mode: str, raw: str | None) -> str | None:
    n = _text(raw, 30)
    if n is None:
        return None
    n = n.upper()
    if mode == "train" and not TRAIN_NO.fullmatch(n):
        raise TicketError("A train number is 5 digits, like 12951.")
    if mode == "flight" and not FLIGHT_NO.fullmatch(n):
        raise TicketError("A flight number looks like 6E 2134 or AI 101.")
    return n


def _check_trip(db: Session, user_id: uuid.UUID, trip_id: uuid.UUID) -> None:
    from app.services.group_service import role_on

    trip = db.get(Trip, trip_id)
    if trip is None or role_on(db, user_id, trip) is None:
        raise TicketError("That trip isn't one of yours.")


def list_for(db: Session, user_id: uuid.UUID, trip_id: uuid.UUID | None = None) -> list[Ticket]:
    q = select(Ticket).where(Ticket.user_id == user_id)
    if trip_id is not None:
        q = q.where(Ticket.trip_id == trip_id)
    rows = list(db.scalars(q))
    # Soonest first; tickets without a date at the end.
    rows.sort(key=lambda t: (t.depart_at is None, t.depart_at or datetime.max, t.created_at))
    return rows


def get_own(db: Session, user_id: uuid.UUID, ticket_id: uuid.UUID) -> Ticket:
    t = db.get(Ticket, ticket_id)
    if t is None or t.user_id != user_id:
        raise TicketNotFound("Ticket not found")
    return t


def save(db: Session, user_id: uuid.UUID, data: TicketInput, file: bytes | None, ticket: Ticket | None = None) -> Ticket:
    vault._fernet()  # noqa: SLF001 -- refuse early when encryption is off
    if data.mode not in MODES:
        raise TicketError("Unknown ticket type")
    pnr = clean_pnr(data.mode, data.pnr)
    number = clean_number(data.mode, data.number)
    if data.depart_at and data.arrive_at and data.arrive_at < data.depart_at:
        raise TicketError("The arrival / check-out time is before the departure / check-in.")
    if data.trip_id is not None:
        _check_trip(db, user_id, data.trip_id)

    if ticket is None:
        if not (pnr or number or data.provider or file):
            raise TicketError("Add at least the PNR, the number, the operator or the e-ticket.")
        ticket = Ticket(user_id=user_id, mode=data.mode)
        db.add(ticket)
    if pnr is not None:
        ticket.pnr_enc = vault.encrypt(pnr.encode()).decode()
        ticket.status = ticket.status_checked_at = None
    if number is not None:
        ticket.number = number
    for field, limit in (("provider", 80), ("from_place", 120), ("to_place", 120), ("seat", 60), ("travel_class", 30)):
        v = getattr(data, field)
        if v is not None:
            setattr(ticket, field, _text(v, limit))
    if data.notes is not None:
        ticket.notes = data.notes.strip()[:1000] or None
    if data.depart_at is not None:
        ticket.depart_at = data.depart_at
    if data.arrive_at is not None:
        ticket.arrive_at = data.arrive_at
    if data.passengers is not None:
        ticket.passengers = max(1, min(int(data.passengers), 50))
    if data.fare is not None:
        ticket.fare = max(0.0, float(data.fare))
    if data.trip_id is not None:
        ticket.trip_id = data.trip_id
    elif data.clear_trip:
        ticket.trip_id = None
    old_file = None
    if file:
        old_file = ticket.file_name
        ticket.file_name, ticket.file_type, ticket.file_size = vault._write(file)  # noqa: SLF001
    db.commit()
    db.refresh(ticket)
    vault._remove(old_file)  # noqa: SLF001
    return ticket


def pnr_of(t: Ticket) -> str | None:
    return vault.decrypt(t.pnr_enc.encode()).decode() if t.pnr_enc else None


def delete(db: Session, t: Ticket) -> None:
    name = t.file_name
    db.delete(t)
    db.commit()
    vault._remove(name)  # noqa: SLF001


def delete_all_files_for_user(db: Session, user_id: uuid.UUID) -> None:
    for t in list_for(db, user_id):
        vault._remove(t.file_name)  # noqa: SLF001


def read_file(t: Ticket) -> bytes:
    if not t.file_name:
        raise TicketNotFound("No e-ticket saved for this booking")
    path = vault.settings.PRIVATE_DOCS_DIR / t.file_name
    if not path.is_file():
        raise TicketNotFound("The file is missing")
    return vault.decrypt(path.read_bytes())


def refresh_pnr(db: Session, t: Ticket) -> dict:
    """Train only: ask the live train API for the PNR's status. Without a
    RAPIDAPI_KEY, or if the API can't answer, the official enquiry page is
    returned to open instead."""
    from app.rail import irctc

    if t.mode != "train" or not t.pnr_enc:
        raise TicketError("Only a train ticket with a PNR can be checked.")
    pnr = pnr_of(t)
    if not irctc.configured():
        return {"status": t.status, "live": False, "enquiry_url": PNR_ENQUIRY,
                "message": "Live PNR status needs a RAPIDAPI_KEY. Open the official enquiry page instead."}
    try:
        summary = irctc.pnr_status(pnr)
    except Exception:  # noqa: BLE001 -- the official page is always the fallback
        return {"status": t.status, "live": False, "enquiry_url": PNR_ENQUIRY,
                "message": "The live status service didn't answer. Check it on the official page."}
    t.status = summary[:120]
    t.status_checked_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": t.status, "live": True, "enquiry_url": PNR_ENQUIRY, "message": None}
