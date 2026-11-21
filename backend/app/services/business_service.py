"""Business accounts: sign-up, the public handle, and who may publish."""
from __future__ import annotations

import re
import uuid

from fastapi import Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.business import BusinessProfile
from app.models.package import PackageBooking, TravelPackage
from app.models.user import User
from app.schemas.business import BusinessFields, BusinessOut, BusinessPublic


def slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return (s or "business")[:60]


def unique_slug(db: Session, name: str, *, keep_for: uuid.UUID | None = None) -> str:
    base = slugify(name)
    slug, n = base, 2
    while True:
        row = db.scalar(select(BusinessProfile).where(BusinessProfile.slug == slug))
        if row is None or row.user_id == keep_for:
            return slug
        slug = f"{base}-{n}"
        n += 1


def apply_fields(profile: BusinessProfile, f: BusinessFields) -> None:
    profile.business_name = f.business_name
    profile.kind = f.kind
    profile.city = f.city
    profile.phone = f.business_phone
    profile.description = f.description.strip()
    profile.website = f.website
    profile.gst_number = f.gst_number


def to_out(db: Session, p: BusinessProfile, owner: User | None = None) -> BusinessOut:
    owner = owner or db.get(User, p.user_id)
    packages = db.scalar(select(func.count()).select_from(TravelPackage).where(TravelPackage.owner_id == p.user_id)) or 0
    pending = db.scalar(
        select(func.count()).select_from(PackageBooking)
        .join(TravelPackage, TravelPackage.id == PackageBooking.package_id)
        .where(TravelPackage.owner_id == p.user_id, PackageBooking.status == "pending")
    ) or 0
    return BusinessOut(
        owner_blocked=bool(owner and owner.is_blocked), is_visible=is_visible(p, owner),
        user_id=str(p.user_id), business_name=p.business_name, slug=p.slug, kind=p.kind, city=p.city,
        business_phone=p.phone, description=p.description, website=p.website, gst_number=p.gst_number,
        status=p.status, status_reason=p.status_reason, created_at=p.created_at, reviewed_at=p.reviewed_at,
        owner_name=owner.name if owner else None, owner_email=owner.email if owner else None,
        package_count=packages, bookings_pending=pending,
    )


def to_public(p: BusinessProfile) -> BusinessPublic:
    return BusinessPublic(
        business_name=p.business_name, slug=p.slug, kind=p.kind, city=p.city,
        description=p.description, website=p.website, since=p.created_at,
    )


def is_visible(p: BusinessProfile | None, owner: User | None) -> bool:
    """The one rule for whether travellers may see a business: approved by the
    admin AND its owner's login not blocked. Suspended, rejected, pending or
    blocked -> its public page, packages and booking are all hidden."""
    return p is not None and p.status == "approved" and owner is not None and not owner.is_blocked


def is_listed(db: Session, owner_id: uuid.UUID | None) -> bool:
    """Platform (admin) packages are always listed; a business's only while visible."""
    if owner_id is None:
        return True
    return is_visible(db.get(BusinessProfile, owner_id), db.get(User, owner_id))


# --- dependencies --------------------------------------------------------------

def current_business(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> BusinessProfile:
    if user.role != "business":
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Business account required")
    p = db.get(BusinessProfile, user.id)
    if p is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Business profile missing")
    return p


def approved_business(p: BusinessProfile = Depends(current_business)) -> BusinessProfile:
    if p.status != "approved":
        msg = {
            "pending": "Your business is waiting for approval. You can publish once it is approved.",
            "rejected": "Your business application was not approved.",
            "suspended": "Your business account is suspended.",
        }.get(p.status, "Your business is not approved yet.")
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=msg)
    return p
