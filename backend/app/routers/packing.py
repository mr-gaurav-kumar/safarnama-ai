"""Packing lists.

  /trips/{id}/packing...        a traveller's own list for a trip they own or
                                have joined (each member has their own list)
  /admin/packing-defaults...    items the admin puts on everyone's list, or on
                                one person's; only the admin can remove them
"""
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_admin
from app.models.packing import PackingDefault, PackingItem
from app.models.risk import AdminAction
from app.models.trip import Trip
from app.models.user import User
from app.schemas.packing import (
    BulkIn, DefaultIn, DefaultOut, DefaultUpdate, ItemIn, ItemUpdate, PackingList, Suggestions,
)
from app.services import group_service, packing_service
from app.services.packing_service import ItemLocked, ItemNotFound, PackingError

router = APIRouter(prefix="/trips/{trip_id}/packing", tags=["packing"])
admin_router = APIRouter(prefix="/admin/packing-defaults", tags=["admin"], dependencies=[Depends(require_admin)])


def _trip(db: Session, user: User, trip_id: uuid.UUID) -> Trip:
    try:
        trip, _role = group_service.trip_for(db, user.id, trip_id)
    except group_service.TripNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Trip not found") from None
    return trip


def _fail(exc: PackingError) -> HTTPException:
    if isinstance(exc, ItemNotFound):
        return HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, ItemLocked):
        return HTTPException(status.HTTP_403_FORBIDDEN, detail=str(exc))
    return HTTPException(status.HTTP_409_CONFLICT, detail=str(exc))


# ---------------------------------------------------------------- traveller

@router.get("", response_model=PackingList)
def get_packing_list(trip_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> PackingList:
    return packing_service.get_list(db, _trip(db, user, trip_id), user.id)


@router.post("", response_model=PackingList, status_code=status.HTTP_201_CREATED)
def add_item(
    trip_id: uuid.UUID, payload: ItemIn, user: User = Depends(get_current_user), db: Session = Depends(get_db),
) -> PackingList:
    trip = _trip(db, user, trip_id)
    try:
        if packing_service.add_items(db, trip, user.id, [payload], "mine") == 0:
            raise PackingError(f"“{payload.name}” is already on your list")
    except PackingError as exc:
        raise _fail(exc) from None
    return packing_service.get_list(db, trip, user.id)


@router.post("/bulk", response_model=PackingList, status_code=status.HTTP_201_CREATED)
def add_many(
    trip_id: uuid.UUID, payload: BulkIn, user: User = Depends(get_current_user), db: Session = Depends(get_db),
) -> PackingList:
    trip = _trip(db, user, trip_id)
    try:
        packing_service.add_items(db, trip, user.id, payload.items, payload.source)
    except PackingError as exc:
        raise _fail(exc) from None
    return packing_service.get_list(db, trip, user.id)


@router.get("/suggestions", response_model=Suggestions)
def suggestions(trip_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Suggestions:
    return packing_service.suggest(db, _trip(db, user, trip_id), user.id)


@router.patch("/{item_id}", response_model=PackingList)
def update_item(
    trip_id: uuid.UUID, item_id: uuid.UUID, payload: ItemUpdate,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
) -> PackingList:
    trip = _trip(db, user, trip_id)
    try:
        packing_service.update_item(db, trip, user.id, item_id, payload)
    except PackingError as exc:
        raise _fail(exc) from None
    return packing_service.get_list(db, trip, user.id)


@router.delete("/{item_id}", response_model=PackingList)
def delete_item(
    trip_id: uuid.UUID, item_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db),
) -> PackingList:
    trip = _trip(db, user, trip_id)
    try:
        packing_service.delete_item(db, trip, user.id, item_id)
    except PackingError as exc:
        raise _fail(exc) from None
    return packing_service.get_list(db, trip, user.id)


@router.post("/reset/{which}", response_model=PackingList)
def reset(
    trip_id: uuid.UUID, which: Literal["going", "return"],
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
) -> PackingList:
    trip = _trip(db, user, trip_id)
    packing_service.reset_ticks(db, trip, user.id, which)
    return packing_service.get_list(db, trip, user.id)


# ---------------------------------------------------------------- admin

def _default_out(db: Session, d: PackingDefault) -> DefaultOut:
    u = db.get(User, d.user_id) if d.user_id else None
    return DefaultOut(
        id=str(d.id), name=d.name, category=d.category, quantity=d.quantity, note=d.note,
        user_id=str(d.user_id) if d.user_id else None, user_email=u.email if u else None,
        user_name=u.name if u else None, created_at=d.created_at,
    )


def _audit(db: Session, admin: User, action: str, default_id: uuid.UUID, **details: str) -> None:
    db.add(AdminAction(admin_id=admin.id, action=action, target_type="packing_default",
                       target_id=str(default_id), details=details))
    db.commit()


@admin_router.get("", response_model=list[DefaultOut])
def list_defaults(db: Session = Depends(get_db)) -> list[DefaultOut]:
    rows = db.scalars(select(PackingDefault).order_by(PackingDefault.created_at.desc()))
    return [_default_out(db, d) for d in rows]


@admin_router.post("", response_model=DefaultOut, status_code=status.HTTP_201_CREATED)
def create_default(payload: DefaultIn, admin: User = Depends(require_admin), db: Session = Depends(get_db)) -> DefaultOut:
    try:
        target = packing_service.target_user(db, payload.user_email)
    except PackingError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from None
    d = PackingDefault(
        name=payload.name, category=payload.category, quantity=payload.quantity,
        note=(payload.note or "").strip() or None, user_id=target.id if target else None, created_by=admin.id,
    )
    db.add(d)
    db.commit()
    db.refresh(d)
    _audit(db, admin, "packing_default.create", d.id, name=d.name, applies_to=target.email if target else "everyone")
    return _default_out(db, d)


@admin_router.put("/{default_id}", response_model=DefaultOut)
def update_default(
    default_id: uuid.UUID, payload: DefaultUpdate, admin: User = Depends(require_admin), db: Session = Depends(get_db),
) -> DefaultOut:
    d = db.get(PackingDefault, default_id)
    if d is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Default item not found")
    d.name, d.category, d.quantity = payload.name, payload.category, payload.quantity
    d.note = (payload.note or "").strip() or None
    db.commit()
    db.refresh(d)
    _audit(db, admin, "packing_default.update", d.id, name=d.name)
    return _default_out(db, d)


@admin_router.delete("/{default_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_default(default_id: uuid.UUID, admin: User = Depends(require_admin), db: Session = Depends(get_db)) -> Response:
    d = db.get(PackingDefault, default_id)
    if d is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Default item not found")
    name = d.name
    # Removed from every list it was put on (the foreign key cascades too;
    # this keeps it explicit on any database).
    for item in db.scalars(select(PackingItem).where(PackingItem.default_id == d.id)):
        db.delete(item)
    db.delete(d)
    db.commit()
    _audit(db, admin, "packing_default.delete", default_id, name=name)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
