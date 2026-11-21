"""Packages and bookings -- shared by the traveller and admin routes."""
from __future__ import annotations

import uuid
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.business import BusinessProfile
from app.models.package import PackageBooking, TravelPackage
from app.models.user import User
from app.schemas.package import BookingOut, PackageOut


class BookingError(Exception):
    pass


def seats_taken(db: Session, package_id: uuid.UUID) -> int:
    return db.scalar(
        select(func.coalesce(func.sum(PackageBooking.travelers), 0)).where(
            PackageBooking.package_id == package_id, PackageBooking.status != "cancelled",
        )
    ) or 0


def to_out(db: Session, p: TravelPackage) -> PackageOut:
    taken = seats_taken(db, p.id)
    biz = db.get(BusinessProfile, p.owner_id) if p.owner_id else None
    count = db.scalar(select(func.count()).select_from(PackageBooking).where(
        PackageBooking.package_id == p.id, PackageBooking.status != "cancelled")) or 0
    return PackageOut(
        id=str(p.id), title=p.title, destination=p.destination, duration_days=p.duration_days,
        price_per_person=float(p.price_per_person), summary=p.summary, description=p.description,
        inclusions=list(p.inclusions or []), highlights=list(p.highlights or []),
        style_tags=list(p.style_tags or []), images=list(p.images or []), seats=p.seats,
        seats_left=None if p.seats is None else max(p.seats - taken, 0),
        valid_from=p.valid_from, valid_until=p.valid_until, is_active=p.is_active,
        created_at=p.created_at, booking_count=count,
        business_name=biz.business_name if biz else None,
        business_slug=biz.slug if biz else None,
    )


def booking_out(b: PackageBooking, user: User | None = None) -> BookingOut:
    p = b.package
    return BookingOut(
        id=str(b.id), package_id=str(p.id), package_title=p.title, destination=p.destination,
        duration_days=p.duration_days, travelers=b.travelers, start_date=b.start_date,
        end_date=b.start_date + timedelta(days=p.duration_days - 1),
        total_price=float(b.total_price), note=b.note, status=b.status, created_at=b.created_at,
        user_name=user.name if user else None, user_email=user.email if user else None,
    )


def book(db: Session, *, package: TravelPackage, user: User, travelers: int, start: date, note: str | None) -> PackageBooking:
    if not package.is_active:
        raise BookingError("This package is not available right now")
    from app.services.business_service import is_listed

    if not is_listed(db, package.owner_id):
        raise BookingError("This package is not available right now")
    if start < date.today():
        raise BookingError("Pick a start date in the future")
    if package.valid_from and start < package.valid_from:
        raise BookingError(f"This package starts from {package.valid_from:%d %b %Y}")
    if package.valid_until and start > package.valid_until:
        raise BookingError(f"This package runs until {package.valid_until:%d %b %Y}")
    if package.seats is not None and seats_taken(db, package.id) + travelers > package.seats:
        raise BookingError("Not enough seats left for that many travellers")
    booking = PackageBooking(
        package_id=package.id, user_id=user.id, travelers=travelers, start_date=start,
        total_price=float(package.price_per_person) * travelers,
        note=(note or "").strip() or None, status="pending",
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking
