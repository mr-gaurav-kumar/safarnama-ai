"""Travel packages for travellers: browse (public), opt in, see and cancel
your own bookings."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.package import PackageBooking, TravelPackage
from app.models.user import User
from app.schemas.package import BookingIn, BookingOut, PackageOut
from app.services import business_service, package_service

router = APIRouter(prefix="/packages", tags=["packages"])


@router.get("", response_model=list[PackageOut])
def list_packages(db: Session = Depends(get_db)) -> list[PackageOut]:
    rows = db.scalars(
        select(TravelPackage).where(TravelPackage.is_active.is_(True)).order_by(TravelPackage.created_at.desc())
    ).all()
    return [package_service.to_out(db, p) for p in rows if business_service.is_listed(db, p.owner_id)]


@router.get("/bookings/mine", response_model=list[BookingOut])
def my_bookings(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[BookingOut]:
    rows = db.scalars(
        select(PackageBooking).where(PackageBooking.user_id == user.id).order_by(PackageBooking.created_at.desc())
    ).all()
    return [package_service.booking_out(b) for b in rows]


@router.get("/{package_id}", response_model=PackageOut)
def get_package(package_id: uuid.UUID, db: Session = Depends(get_db)) -> PackageOut:
    p = db.get(TravelPackage, package_id)
    if p is None or not p.is_active or not business_service.is_listed(db, p.owner_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Package not found")
    return package_service.to_out(db, p)


@router.post("/{package_id}/book", response_model=BookingOut, status_code=status.HTTP_201_CREATED)
def book_package(
    package_id: uuid.UUID, payload: BookingIn,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
) -> BookingOut:
    p = db.get(TravelPackage, package_id)
    if p is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Package not found")
    try:
        b = package_service.book(db, package=p, user=user, travelers=payload.travelers,
                                 start=payload.start_date, note=payload.note)
    except package_service.BookingError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from None
    return package_service.booking_out(b)


@router.post("/bookings/{booking_id}/cancel", response_model=BookingOut)
def cancel_booking(
    booking_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db),
) -> BookingOut:
    b = db.get(PackageBooking, booking_id)
    if b is None or b.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Booking not found")
    b.status = "cancelled"
    db.commit()
    db.refresh(b)
    return package_service.booking_out(b)
