"""Business / agency accounts: their own profile, packages and bookings, plus
the public business page."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.business import BusinessProfile
from app.models.package import PackageBooking, TravelPackage
from app.models.user import User
from app.schemas.admin import Page
from app.schemas.business import BusinessOut, BusinessPublic, BusinessUpdate
from app.schemas.package import BookingOut, BookingStatusIn, PackageFillIn, PackageIn, PackageOut
from app.services import business_service, package_service
from app.services.business_service import approved_business, current_business

router = APIRouter(prefix="/business", tags=["business"])
public_router = APIRouter(prefix="/businesses", tags=["business"])


# --- profile ------------------------------------------------------------------

@router.get("/me", response_model=BusinessOut)
def my_business(p: BusinessProfile = Depends(current_business), db: Session = Depends(get_db)) -> BusinessOut:
    return business_service.to_out(db, p)


@router.put("/me", response_model=BusinessOut)
def update_business(
    payload: BusinessUpdate, p: BusinessProfile = Depends(current_business), db: Session = Depends(get_db),
) -> BusinessOut:
    renamed = payload.business_name != p.business_name
    business_service.apply_fields(p, payload)
    if renamed:
        p.slug = business_service.unique_slug(db, payload.business_name, keep_for=p.user_id)
    db.commit()
    db.refresh(p)
    return business_service.to_out(db, p)


# --- packages -----------------------------------------------------------------

def _own_package(db: Session, p: BusinessProfile, package_id: uuid.UUID) -> TravelPackage:
    pkg = db.get(TravelPackage, package_id)
    if pkg is None or pkg.owner_id != p.user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Package not found")
    return pkg


@router.get("/packages", response_model=list[PackageOut])
def my_packages(p: BusinessProfile = Depends(current_business), db: Session = Depends(get_db)) -> list[PackageOut]:
    rows = db.scalars(
        select(TravelPackage).where(TravelPackage.owner_id == p.user_id).order_by(TravelPackage.created_at.desc())
    ).all()
    return [package_service.to_out(db, x) for x in rows]


@router.post("/packages/fill")
def fill_package(payload: PackageFillIn, p: BusinessProfile = Depends(current_business)) -> dict:
    """Suggest the blank parts of a package (title, summary, description,
    inclusions, day-by-day, tags). Nothing is saved; filled fields stay as they are."""
    return _fill(payload, p.user_id)


def _fill(payload: PackageFillIn, who: uuid.UUID) -> dict:
    from app.core import ratelimit
    from app.core.config import settings
    from app.llm import package_fill

    if settings.RATE_LIMIT_ENABLED:
        allowed, retry = ratelimit.check("package-fill", str(who), limit=6, window_seconds=60)
        if not allowed:
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, detail=f"Too many at once — try again in {retry}s.")
    return package_fill.fill(payload)


@router.post("/packages", response_model=PackageOut, status_code=status.HTTP_201_CREATED)
def create_package(
    payload: PackageIn, p: BusinessProfile = Depends(approved_business), db: Session = Depends(get_db),
) -> PackageOut:
    pkg = TravelPackage(**payload.model_dump(), owner_id=p.user_id)
    db.add(pkg)
    db.commit()
    db.refresh(pkg)
    return package_service.to_out(db, pkg)


@router.put("/packages/{package_id}", response_model=PackageOut)
def update_package(
    package_id: uuid.UUID, payload: PackageIn,
    p: BusinessProfile = Depends(approved_business), db: Session = Depends(get_db),
) -> PackageOut:
    pkg = _own_package(db, p, package_id)
    for field, value in payload.model_dump().items():
        setattr(pkg, field, value)
    db.commit()
    db.refresh(pkg)
    return package_service.to_out(db, pkg)


@router.delete("/packages/{package_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_package(
    package_id: uuid.UUID, p: BusinessProfile = Depends(current_business), db: Session = Depends(get_db),
) -> None:
    pkg = _own_package(db, p, package_id)
    db.delete(pkg)
    db.commit()


# --- bookings of my packages ------------------------------------------------------

@router.get("/bookings", response_model=Page[BookingOut])
def my_package_bookings(
    booking_status: str | None = Query(default=None, alias="status"),
    limit: int = 25, offset: int = 0,
    p: BusinessProfile = Depends(current_business), db: Session = Depends(get_db),
) -> Page[BookingOut]:
    limit, offset = max(1, min(limit, 100)), max(0, offset)
    where = [TravelPackage.owner_id == p.user_id]
    if booking_status:
        where.append(PackageBooking.status == booking_status)
    base = (
        select(PackageBooking, User)
        .select_from(PackageBooking)
        .join(TravelPackage, TravelPackage.id == PackageBooking.package_id)
        .join(User, User.id == PackageBooking.user_id)
        .where(*where)
    )
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = db.execute(base.order_by(PackageBooking.created_at.desc()).limit(limit).offset(offset)).all()
    return Page(items=[package_service.booking_out(b, u) for b, u in rows], total=total, limit=limit, offset=offset)


@router.put("/bookings/{booking_id}", response_model=BookingOut)
def set_booking_status(
    booking_id: uuid.UUID, payload: BookingStatusIn,
    p: BusinessProfile = Depends(approved_business), db: Session = Depends(get_db),
) -> BookingOut:
    b = db.get(PackageBooking, booking_id)
    if b is None or b.package.owner_id != p.user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Booking not found")
    b.status = payload.status
    db.commit()
    db.refresh(b)
    return package_service.booking_out(b, db.get(User, b.user_id))


# --- public business page -----------------------------------------------------------

@public_router.get("/{slug}")
def business_page(slug: str, db: Session = Depends(get_db)) -> dict:
    p = db.scalar(select(BusinessProfile).where(BusinessProfile.slug == slug.lower()))
    if p is None or not business_service.is_visible(p, db.get(User, p.user_id)):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Business not found")
    rows = db.scalars(
        select(TravelPackage).where(TravelPackage.owner_id == p.user_id, TravelPackage.is_active.is_(True))
        .order_by(TravelPackage.created_at.desc())
    ).all()
    return {
        "business": BusinessPublic.model_validate(business_service.to_public(p)).model_dump(mode="json"),
        "packages": [package_service.to_out(db, x).model_dump(mode="json") for x in rows],
    }
