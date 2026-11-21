"""My tickets: bookings from anywhere, saved by the traveller.

Owner only, like My documents: every route is scoped to the signed-in user,
the PNR and e-ticket are encrypted, and there is no admin route.
"""
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.ticket import Ticket
from app.models.trip import Trip
from app.models.user import User
from app.services import document_vault as vault
from app.services import tickets as svc

router = APIRouter(prefix="/me/tickets", tags=["tickets"])


class TicketOut(BaseModel):
    id: str
    mode: str
    provider: str | None
    number: str | None
    pnr: str | None
    from_place: str | None
    to_place: str | None
    depart_at: datetime | None
    arrive_at: datetime | None
    seat: str | None
    travel_class: str | None
    passengers: int
    fare: float | None
    notes: str | None
    status: str | None
    status_checked_at: datetime | None
    has_file: bool
    file_type: str | None
    trip_id: str | None
    trip_destination: str | None


class TicketList(BaseModel):
    enabled: bool
    live_pnr: bool
    items: list[TicketOut]


def _out(db: Session, t: Ticket) -> TicketOut:
    trip = db.get(Trip, t.trip_id) if t.trip_id else None
    return TicketOut(
        id=str(t.id), mode=t.mode, provider=t.provider, number=t.number, pnr=svc.pnr_of(t),
        from_place=t.from_place, to_place=t.to_place, depart_at=t.depart_at, arrive_at=t.arrive_at,
        seat=t.seat, travel_class=t.travel_class, passengers=t.passengers,
        fare=float(t.fare) if t.fare is not None else None, notes=t.notes, status=t.status,
        status_checked_at=t.status_checked_at, has_file=bool(t.file_name), file_type=t.file_type,
        trip_id=str(t.trip_id) if t.trip_id else None, trip_destination=trip.destination if trip else None,
    )


def _fail(exc: vault.VaultError) -> HTTPException:
    if isinstance(exc, vault.DocumentNotFound):
        return HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, vault.VaultDisabled):
        return HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    return HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


def _uuid(v: str | None) -> uuid.UUID | None:
    if not v:
        return None
    try:
        return uuid.UUID(v)
    except ValueError:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unknown trip") from None


async def _read(upload: UploadFile | None) -> bytes | None:
    if upload is None or not upload.filename:
        return None
    return (await upload.read(vault.MAX_MB * 1024 * 1024 + 1)) or None


def _form(
    mode: str = Form(...),
    provider: str | None = Form(default=None),
    number: str | None = Form(default=None),
    pnr: str | None = Form(default=None),
    from_place: str | None = Form(default=None),
    to_place: str | None = Form(default=None),
    depart_at: datetime | None = Form(default=None),
    arrive_at: datetime | None = Form(default=None),
    seat: str | None = Form(default=None),
    travel_class: str | None = Form(default=None),
    passengers: int | None = Form(default=None, ge=1, le=50),
    fare: float | None = Form(default=None, ge=0, le=10_000_000),
    notes: str | None = Form(default=None, max_length=1000),
    trip_id: str | None = Form(default=None),
) -> svc.TicketInput:
    clear = trip_id == "none"
    return svc.TicketInput(
        mode=mode, provider=provider, number=number, pnr=pnr, from_place=from_place, to_place=to_place,
        depart_at=depart_at, arrive_at=arrive_at, seat=seat, travel_class=travel_class, passengers=passengers,
        fare=fare, notes=notes, trip_id=None if clear else _uuid(trip_id), clear_trip=clear,
    )


@router.get("", response_model=TicketList)
def list_tickets(
    response: Response, trip_id: str | None = Query(default=None),
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
) -> TicketList:
    from app.rail import irctc

    response.headers["Cache-Control"] = "no-store"
    try:
        items = [_out(db, t) for t in svc.list_for(db, user.id, _uuid(trip_id))]
    except vault.VaultError as exc:
        raise _fail(exc) from None
    return TicketList(enabled=vault.enabled(), live_pnr=irctc.configured(), items=items)


@router.post("", response_model=TicketOut, status_code=status.HTTP_201_CREATED)
async def add_ticket(
    data: svc.TicketInput = Depends(_form), file: UploadFile | None = File(default=None),
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
) -> TicketOut:
    try:
        t = svc.save(db, user.id, data, await _read(file))
    except vault.VaultError as exc:
        raise _fail(exc) from None
    return _out(db, t)


@router.put("/{ticket_id}", response_model=TicketOut)
async def update_ticket(
    ticket_id: uuid.UUID, data: svc.TicketInput = Depends(_form), file: UploadFile | None = File(default=None),
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
) -> TicketOut:
    try:
        t = svc.get_own(db, user.id, ticket_id)
        data.mode = t.mode  # the kind of ticket doesn't change
        t = svc.save(db, user.id, data, await _read(file), ticket=t)
    except vault.VaultError as exc:
        raise _fail(exc) from None
    return _out(db, t)


@router.post("/{ticket_id}/pnr-status")
def pnr_status(ticket_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    try:
        return svc.refresh_pnr(db, svc.get_own(db, user.id, ticket_id))
    except vault.VaultError as exc:
        raise _fail(exc) from None


@router.get("/{ticket_id}/file")
def ticket_file(ticket_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Response:
    try:
        t = svc.get_own(db, user.id, ticket_id)
        data = svc.read_file(t)
    except vault.VaultError as exc:
        raise _fail(exc) from None
    ext = {"application/pdf": "pdf", "image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}.get(t.file_type or "", "bin")
    return Response(
        content=data, media_type=t.file_type or "application/octet-stream",
        headers={"Content-Disposition": f'inline; filename="ticket.{ext}"', "Cache-Control": "no-store",
                 "X-Content-Type-Options": "nosniff"},
    )


@router.delete("/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ticket(ticket_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Response:
    try:
        svc.delete(db, svc.get_own(db, user.id, ticket_id))
    except vault.VaultError as exc:
        raise _fail(exc) from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)
