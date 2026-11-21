"""Admin dashboard API (§4.14, §6.1).

Every route depends on `require_admin`, which re-reads the user's role from
the database on each request -- the frontend's admin guard is only cosmetic.
Every change is written to admin_actions. An admin cannot block, demote or
delete their own account, so the last admin can never lock everyone out.
"""

import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_admin
from app.models.chat import ChatMessage, SupportEscalation
from app.models.group import TripCollaborator, TripFeedback
from app.models.business import BusinessProfile
from app.models.package import PackageBooking, TravelPackage
from app.models.risk import ActivityEvent, AdminAction, FraudFlag
from app.models.trip import Trip
from app.models.user import User
from app.rag import retrieval
from app.schemas.admin import (
    AdminChatLine, AdminEscalation, AdminFeedback, AdminFlag, AdminTrip, AdminTripDetail, AdminUser,
    AdminUserDetail, AuditLine,
    EscalationUpdate, FlagUpdate, Page, Stats, TripUpdate, UserCreate, UserUpdate,
)
from app.core.security import hash_password
from app.schemas.trip import MAX_TRIP_DAYS, TripCreate
from app.schemas.package import BookingOut, BookingStatusIn, PackageFillIn, PackageIn, PackageOut
from app.schemas.business import AdminBusinessCreate, BusinessBlockIn, BusinessOut, BusinessStatusIn, BusinessUpdate
from app.services import business_service, package_service, session_service, trip_service, user_service
from app.tasks import jobs
from app.tasks.dispatch import enqueue

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])

MAX_LIMIT = 100


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _audit(db: Session, admin: User, action: str, target_type: str, target_id: object, **details) -> None:
    db.add(AdminAction(admin_id=admin.id, action=action, target_type=target_type,
                       target_id=str(target_id), details=details))
    db.commit()


def _get(db: Session, model, obj_id: uuid.UUID, what: str):
    row = db.get(model, obj_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"{what} not found")
    return row


def _page(limit: int, offset: int) -> tuple[int, int]:
    return min(max(limit, 1), MAX_LIMIT), max(offset, 0)


# --- stats -----------------------------------------------------------------------

@router.get("/stats", response_model=Stats)
def stats(db: Session = Depends(get_db)) -> Stats:
    count = lambda q: db.scalar(q) or 0  # noqa: E731
    return Stats(
        users_total=count(select(func.count()).select_from(User)),
        users_blocked=count(select(func.count()).select_from(User).where(User.is_blocked.is_(True))),
        signups_7d=count(select(func.count()).select_from(User)
                         .where(User.created_at >= _now() - timedelta(days=7))),
        trips_total=count(select(func.count()).select_from(Trip)),
        trips_active=count(select(func.count()).select_from(Trip).where(Trip.end_date >= date.today())),
        trips_processing=count(select(func.count()).select_from(Trip).where(Trip.status == "processing")),
        open_fraud_flags=count(select(func.count()).select_from(FraudFlag).where(FraudFlag.status == "open")),
        open_escalations=count(select(func.count()).select_from(SupportEscalation)
                               .where(SupportEscalation.status == "open")),
        packages_active=count(select(func.count()).select_from(TravelPackage)
                              .where(TravelPackage.is_active.is_(True))),
        bookings_pending=count(select(func.count()).select_from(PackageBooking)
                               .where(PackageBooking.status == "pending")),
        businesses_pending=count(select(func.count()).select_from(BusinessProfile)
                                 .where(BusinessProfile.status == "pending")),
    )


# --- users ------------------------------------------------------------------------

def _admin_user(db: Session, u: User) -> AdminUser:
    return AdminUser(
        id=str(u.id), name=u.name, email=u.email, role=u.role, is_verified=u.is_verified,
        is_blocked=u.is_blocked, created_at=u.created_at,
        trip_count=db.scalar(select(func.count()).select_from(Trip).where(Trip.user_id == u.id)) or 0,
        open_flags=db.scalar(select(func.count()).select_from(FraudFlag)
                             .where(FraudFlag.user_id == u.id, FraudFlag.status == "open")) or 0,
        home_town=u.home_town, avatar_url=u.avatar_url,
    )


@router.get("/users", response_model=Page[AdminUser])
def list_users(
    q: str = "", limit: int = 25, offset: int = 0, db: Session = Depends(get_db),
) -> Page[AdminUser]:
    limit, offset = _page(limit, offset)
    where = []
    if q.strip():
        like = f"%{q.strip().lower()}%"
        where.append(or_(func.lower(User.email).like(like), func.lower(User.name).like(like)))
    total = db.scalar(select(func.count()).select_from(User).where(*where)) or 0
    rows = db.scalars(select(User).where(*where).order_by(User.created_at.desc())
                      .limit(limit).offset(offset)).all()
    return Page(items=[_admin_user(db, u) for u in rows], total=total, limit=limit, offset=offset)


@router.get("/users/{user_id}", response_model=AdminUserDetail)
def get_user(user_id: uuid.UUID, db: Session = Depends(get_db)) -> AdminUserDetail:
    """One account in full: profile, sign-in activity and every trip they own."""
    u = _get(db, User, user_id, "User")
    base = _admin_user(db, u)
    trips = db.scalars(select(Trip).where(Trip.user_id == u.id).order_by(Trip.created_at.desc())).all()
    logins = select(ActivityEvent).where(ActivityEvent.user_id == u.id, ActivityEvent.kind == "login_ok")
    last = db.scalars(logins.order_by(ActivityEvent.created_at.desc()).limit(1)).first()
    return AdminUserDetail(
        **base.model_dump(),
        updated_at=u.updated_at,
        date_of_birth=u.date_of_birth,
        phone=u.phone,
        gender=u.gender,
        travel_interests=u.travel_interests,
        last_login_at=last.created_at if last else None,
        login_count=db.scalar(select(func.count()).select_from(logins.subquery())) or 0,
        trips=[
            AdminTripDetail(
                id=str(t.id), destination=t.destination, start_date=t.start_date, end_date=t.end_date,
                status=t.status, plan_status=t.plan_status, budget=float(t.budget), use_memory=t.use_memory,
                travelers=t.travelers, style_tags=list(t.style_tags or []), created_at=t.created_at,
            )
            for t in trips
        ],
    )


@router.post("/users", response_model=AdminUser, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, admin: User = Depends(require_admin), db: Session = Depends(get_db)) -> AdminUser:
    try:
        u = user_service.create_user(
            db, name=payload.name, email=payload.email, password=payload.password,
            home_town=(payload.home_town or "").strip() or None, phone=(payload.phone or "").strip() or None,
        )
    except user_service.EmailAlreadyRegistered:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="An account with this email already exists") from None
    u.is_verified = payload.is_verified
    db.commit()
    _audit(db, admin, "user.create", "user", u.id, email=u.email)
    return _admin_user(db, u)


@router.put("/users/{user_id}", response_model=AdminUser)
def update_user(
    user_id: uuid.UUID, payload: UserUpdate,
    admin: User = Depends(require_admin), db: Session = Depends(get_db),
) -> AdminUser:
    u = _get(db, User, user_id, "User")
    changes = payload.model_dump(exclude_none=True)
    if u.id == admin.id and changes.get("is_blocked"):
        raise HTTPException(status.HTTP_409_CONFLICT, detail="You can't block your own account")
    new_password = changes.pop("password", None)
    if "email" in changes:
        changes["email"] = changes["email"].lower()
        other = user_service.get_by_email(db, changes["email"])
        if other is not None and other.id != u.id:
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Another account already uses that email")
    for field, value in changes.items():
        setattr(u, field, value)
    if new_password:
        u.password_hash = hash_password(new_password)
    db.commit()
    if changes.get("is_blocked") or new_password:
        session_service.revoke_all_for_user(db, u.id, reason="admin")
    if new_password:
        changes["password"] = "changed"
    _audit(db, admin, "user.update", "user", u.id, **{k: str(v) for k, v in changes.items()})
    return _admin_user(db, u)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: uuid.UUID, admin: User = Depends(require_admin), db: Session = Depends(get_db)) -> None:
    u = _get(db, User, user_id, "User")
    if u.id == admin.id:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="You can't delete your own account here")
    email = u.email
    from app.services.document_vault import delete_all_for_user

    delete_all_for_user(db, u.id)  # their encrypted files; the rows go with the cascade
    from app.services.tickets import delete_all_files_for_user as delete_ticket_files

    delete_ticket_files(db, u.id)
    from app.services import avatar as avatar_files

    avatar_files.remove(u.avatar_url)
    db.delete(u)
    db.commit()
    _audit(db, admin, "user.delete", "user", user_id, email=email)


# --- trips -------------------------------------------------------------------------

def _admin_trip(db: Session, t: Trip, owner_email: str) -> AdminTrip:
    members = db.scalar(select(func.count()).select_from(TripCollaborator).where(
        TripCollaborator.trip_id == t.id, TripCollaborator.status == "joined")) or 0
    return AdminTrip(
        id=str(t.id), destination=t.destination, start_date=t.start_date, end_date=t.end_date,
        status=t.status, plan_status=t.plan_status, owner_email=owner_email,
        member_count=members, created_at=t.created_at, error=t.error,
        budget=float(t.budget), travelers=t.travelers, style_tags=list(t.style_tags or []),
    )


@router.get("/trips", response_model=Page[AdminTrip])
def list_trips(
    q: str = "", trip_status: str | None = Query(default=None, alias="status"),
    limit: int = 25, offset: int = 0, db: Session = Depends(get_db),
) -> Page[AdminTrip]:
    limit, offset = _page(limit, offset)
    where = []
    if q.strip():
        like = f"%{q.strip().lower()}%"
        where.append(or_(func.lower(Trip.destination).like(like), func.lower(User.email).like(like)))
    if trip_status:
        where.append(Trip.status == trip_status)
    base = select(Trip, User.email).join(User, User.id == Trip.user_id).where(*where)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = db.execute(base.order_by(Trip.created_at.desc()).limit(limit).offset(offset)).all()
    return Page(items=[_admin_trip(db, t, e) for t, e in rows], total=total, limit=limit, offset=offset)


@router.get("/trips/{trip_id}", response_model=AdminTrip)
def get_trip(trip_id: uuid.UUID, db: Session = Depends(get_db)) -> AdminTrip:
    t = _get(db, Trip, trip_id, "Trip")
    return _admin_trip(db, t, db.get(User, t.user_id).email)


@router.put("/trips/{trip_id}", response_model=AdminTrip)
def update_trip(
    trip_id: uuid.UUID, payload: TripUpdate,
    admin: User = Depends(require_admin), db: Session = Depends(get_db),
) -> AdminTrip:
    """Correct a trip -- e.g. mark one stuck in 'processing' as failed so its
    owner can plan it again."""
    t = _get(db, Trip, trip_id, "Trip")
    changes = payload.model_dump(exclude_none=True)
    start = changes.get("start_date", t.start_date)
    end = changes.get("end_date", t.end_date)
    if end < start:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="End date must not be before start date")
    if (end - start).days + 1 > MAX_TRIP_DAYS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Trips longer than {MAX_TRIP_DAYS} days are not supported")
    if "destination" in changes:
        changes["destination"] = changes["destination"].strip()
    for field, value in changes.items():
        setattr(t, field, value)
    if changes.get("status") == "failed" and not t.error:
        t.error = "Stopped by support. Please plan this trip again."
    db.commit()
    _audit(db, admin, "trip.update", "trip", t.id, **{k: str(v) for k, v in changes.items()})
    return _admin_trip(db, t, db.get(User, t.user_id).email)


@router.post("/users/{user_id}/trips", response_model=AdminTrip, status_code=status.HTTP_202_ACCEPTED)
def create_trip_for_user(
    user_id: uuid.UUID, payload: TripCreate, background: BackgroundTasks,
    admin: User = Depends(require_admin), db: Session = Depends(get_db),
) -> AdminTrip:
    """Plan a trip on a traveller's behalf -- it is generated exactly as if
    they had asked for it, and shows up in their dashboard."""
    u = _get(db, User, user_id, "User")
    t = trip_service.create_trip(db, user_id=u.id, payload=payload)
    enqueue(background, jobs.run_trip_generation, str(t.id))
    _audit(db, admin, "trip.create", "trip", t.id, owner=u.email, destination=t.destination)
    return _admin_trip(db, t, u.email)


@router.post("/trips/{trip_id}/replan", response_model=AdminTrip, status_code=status.HTTP_202_ACCEPTED)
def replan_trip(
    trip_id: uuid.UUID, background: BackgroundTasks,
    admin: User = Depends(require_admin), db: Session = Depends(get_db),
) -> AdminTrip:
    """Generate the itinerary again, e.g. after editing the trip's details."""
    t = _get(db, Trip, trip_id, "Trip")
    t.status = "processing"
    t.error = None
    db.commit()
    enqueue(background, jobs.run_trip_generation, str(t.id))
    _audit(db, admin, "trip.replan", "trip", t.id)
    return _admin_trip(db, t, db.get(User, t.user_id).email)


@router.delete("/trips/{trip_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_trip(trip_id: uuid.UUID, admin: User = Depends(require_admin), db: Session = Depends(get_db)) -> None:
    t = _get(db, Trip, trip_id, "Trip")
    dest = t.destination
    db.delete(t)
    db.commit()
    _audit(db, admin, "trip.delete", "trip", trip_id, destination=dest)


# --- fraud flags -------------------------------------------------------------------

@router.get("/fraud-flags", response_model=Page[AdminFlag])
def list_flags(
    flag_status: str | None = Query(default="open", alias="status"),
    limit: int = 25, offset: int = 0, db: Session = Depends(get_db),
) -> Page[AdminFlag]:
    limit, offset = _page(limit, offset)
    where = [FraudFlag.status == flag_status] if flag_status else []
    total = db.scalar(select(func.count()).select_from(FraudFlag).where(*where)) or 0
    rows = db.execute(
        select(FraudFlag, User).join(User, User.id == FraudFlag.user_id).where(*where)
        .order_by(FraudFlag.risk_score.desc(), FraudFlag.created_at.desc()).limit(limit).offset(offset)
    ).all()
    return Page(items=[AdminFlag(
        id=str(f.id), user_id=str(f.user_id), user_email=u.email, user_blocked=u.is_blocked,
        trip_id=str(f.trip_id) if f.trip_id else None, reason=f.reason, risk_score=f.risk_score,
        details=f.details, status=f.status, created_at=f.created_at, reviewed_at=f.reviewed_at,
    ) for f, u in rows], total=total, limit=limit, offset=offset)


@router.put("/fraud-flags/{flag_id}", response_model=AdminFlag)
def review_flag(
    flag_id: uuid.UUID, payload: FlagUpdate,
    admin: User = Depends(require_admin), db: Session = Depends(get_db),
) -> AdminFlag:
    """Resolve or dismiss a flag -- and, from the same screen, block the user."""
    f = _get(db, FraudFlag, flag_id, "Flag")
    u = db.get(User, f.user_id)
    if payload.block_user and u.id == admin.id:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="You can't block your own account")
    f.status = payload.status
    f.reviewed_by = admin.id
    f.reviewed_at = _now()
    if payload.block_user:
        u.is_blocked = True
    db.commit()
    if payload.block_user:
        session_service.revoke_all_for_user(db, u.id)
    _audit(db, admin, "flag.review", "fraud_flag", f.id, status=f.status, block_user=payload.block_user)
    return AdminFlag(
        id=str(f.id), user_id=str(f.user_id), user_email=u.email, user_blocked=u.is_blocked,
        trip_id=str(f.trip_id) if f.trip_id else None, reason=f.reason, risk_score=f.risk_score,
        details=f.details, status=f.status, created_at=f.created_at, reviewed_at=f.reviewed_at,
    )


# --- support escalations --------------------------------------------------------------

@router.get("/escalations", response_model=Page[AdminEscalation])
def list_escalations(
    esc_status: str | None = Query(default="open", alias="status"),
    limit: int = 25, offset: int = 0, db: Session = Depends(get_db),
) -> Page[AdminEscalation]:
    limit, offset = _page(limit, offset)
    where = [SupportEscalation.status == esc_status] if esc_status else []
    total = db.scalar(select(func.count()).select_from(SupportEscalation).where(*where)) or 0
    rows = db.execute(
        select(SupportEscalation, User.email).join(User, User.id == SupportEscalation.user_id)
        .where(*where).order_by(SupportEscalation.created_at.desc()).limit(limit).offset(offset)
    ).all()
    return Page(items=[AdminEscalation(
        id=str(e.id), user_email=email, reason=e.reason, intent=e.intent, excerpt=e.excerpt,
        status=e.status, created_at=e.created_at,
    ) for e, email in rows], total=total, limit=limit, offset=offset)


@router.put("/escalations/{esc_id}", response_model=AdminEscalation)
def update_escalation(
    esc_id: uuid.UUID, payload: EscalationUpdate,
    admin: User = Depends(require_admin), db: Session = Depends(get_db),
) -> AdminEscalation:
    e = _get(db, SupportEscalation, esc_id, "Escalation")
    e.status = payload.status
    e.resolved_at = _now() if payload.status == "resolved" else None
    db.commit()
    _audit(db, admin, "escalation.update", "escalation", e.id, status=e.status)
    return AdminEscalation(
        id=str(e.id), user_email=db.get(User, e.user_id).email, reason=e.reason, intent=e.intent,
        excerpt=e.excerpt, status=e.status, created_at=e.created_at,
    )


# --- feedback ------------------------------------------------------------------------

@router.get("/feedback", response_model=Page[AdminFeedback])
def list_feedback(limit: int = 25, offset: int = 0, db: Session = Depends(get_db)) -> Page[AdminFeedback]:
    limit, offset = _page(limit, offset)
    total = db.scalar(select(func.count()).select_from(TripFeedback)) or 0
    rows = db.execute(
        select(TripFeedback, Trip.destination, User.email)
        .join(Trip, Trip.id == TripFeedback.trip_id).join(User, User.id == TripFeedback.user_id)
        .order_by(TripFeedback.created_at.desc()).limit(limit).offset(offset)
    ).all()
    return Page(items=[AdminFeedback(
        id=str(f.id), trip_id=str(f.trip_id), destination=dest, user_email=email,
        rating=f.rating, comment=f.comment, created_at=f.created_at,
    ) for f, dest, email in rows], total=total, limit=limit, offset=offset)


@router.delete("/feedback/{feedback_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_feedback(feedback_id: uuid.UUID, admin: User = Depends(require_admin), db: Session = Depends(get_db)) -> None:
    """Remove spam or abusive feedback. If it was the owner's, their memory is
    rebuilt without it, so a removed rating stops steering their plans."""
    f = _get(db, TripFeedback, feedback_id, "Feedback")
    trip = db.get(Trip, f.trip_id)
    was_owners = trip is not None and f.user_id == trip.user_id
    db.delete(f)
    db.commit()
    if was_owners and trip.status == "completed":
        retrieval.store_trip_embedding(db, trip)
    _audit(db, admin, "feedback.delete", "feedback", feedback_id)


# --- chat logs -------------------------------------------------------------------------

@router.get("/chat-logs", response_model=Page[AdminChatLine])
def chat_logs(
    q: str = "", user_email: str = "", limit: int = 50, offset: int = 0,
    db: Session = Depends(get_db),
) -> Page[AdminChatLine]:
    limit, offset = _page(limit, offset)
    where = []
    if q.strip():
        where.append(func.lower(ChatMessage.message).like(f"%{q.strip().lower()}%"))
    if user_email.strip():
        where.append(User.email == user_email.strip().lower())
    base = select(ChatMessage, User.email).join(User, User.id == ChatMessage.user_id).where(*where)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = db.execute(base.order_by(ChatMessage.created_at.desc()).limit(limit).offset(offset)).all()
    return Page(items=[AdminChatLine(
        id=str(m.id), user_email=email, sender=m.sender, message=m.message,
        intent=m.intent, sentiment=m.sentiment, created_at=m.created_at,
    ) for m, email in rows], total=total, limit=limit, offset=offset)


# --- audit -----------------------------------------------------------------------------

@router.get("/audit", response_model=Page[AuditLine])
def audit(limit: int = 50, offset: int = 0, db: Session = Depends(get_db)) -> Page[AuditLine]:
    limit, offset = _page(limit, offset)
    total = db.scalar(select(func.count()).select_from(AdminAction)) or 0
    rows = db.execute(
        select(AdminAction, User.email).outerjoin(User, User.id == AdminAction.admin_id)
        .order_by(AdminAction.created_at.desc()).limit(limit).offset(offset)
    ).all()
    return Page(items=[AuditLine(
        id=str(a.id), admin_email=email, action=a.action, target_type=a.target_type,
        target_id=a.target_id, details=a.details, created_at=a.created_at,
    ) for a, email in rows], total=total, limit=limit, offset=offset)


# --- travel packages ---------------------------------------------------------------

@router.get("/packages", response_model=list[PackageOut])
def admin_list_packages(db: Session = Depends(get_db)) -> list[PackageOut]:
    rows = db.scalars(select(TravelPackage).order_by(TravelPackage.created_at.desc())).all()
    return [package_service.to_out(db, p) for p in rows]


@router.post("/packages/fill")
def admin_fill_package(payload: PackageFillIn, admin: User = Depends(require_admin)) -> dict:
    """The same suggestions merchants get, for the admin's own packages."""
    from app.routers.business import _fill

    return _fill(payload, admin.id)


@router.post("/packages", response_model=PackageOut, status_code=status.HTTP_201_CREATED)
def admin_create_package(
    payload: PackageIn, admin: User = Depends(require_admin), db: Session = Depends(get_db),
) -> PackageOut:
    p = TravelPackage(**payload.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    _audit(db, admin, "package.create", "package", p.id, title=p.title)
    return package_service.to_out(db, p)


@router.put("/packages/{package_id}", response_model=PackageOut)
def admin_update_package(
    package_id: uuid.UUID, payload: PackageIn,
    admin: User = Depends(require_admin), db: Session = Depends(get_db),
) -> PackageOut:
    p = _get(db, TravelPackage, package_id, "Package")
    for field, value in payload.model_dump().items():
        setattr(p, field, value)
    db.commit()
    db.refresh(p)
    _audit(db, admin, "package.update", "package", p.id, title=p.title, active=p.is_active)
    return package_service.to_out(db, p)


@router.delete("/packages/{package_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_package(
    package_id: uuid.UUID, admin: User = Depends(require_admin), db: Session = Depends(get_db),
) -> None:
    p = _get(db, TravelPackage, package_id, "Package")
    title = p.title
    db.delete(p)
    db.commit()
    _audit(db, admin, "package.delete", "package", package_id, title=title)


@router.get("/package-bookings", response_model=Page[BookingOut])
def admin_list_bookings(
    booking_status: str | None = Query(default=None, alias="status"),
    limit: int = 25, offset: int = 0, db: Session = Depends(get_db),
) -> Page[BookingOut]:
    limit, offset = _page(limit, offset)
    where = [PackageBooking.status == booking_status] if booking_status else []
    total = db.scalar(select(func.count()).select_from(PackageBooking).where(*where)) or 0
    rows = db.execute(
        select(PackageBooking, User).join(User, User.id == PackageBooking.user_id).where(*where)
        .order_by(PackageBooking.created_at.desc()).limit(limit).offset(offset)
    ).all()
    return Page(items=[package_service.booking_out(b, u) for b, u in rows], total=total, limit=limit, offset=offset)


@router.put("/package-bookings/{booking_id}", response_model=BookingOut)
def admin_update_booking(
    booking_id: uuid.UUID, payload: BookingStatusIn,
    admin: User = Depends(require_admin), db: Session = Depends(get_db),
) -> BookingOut:
    b = _get(db, PackageBooking, booking_id, "Booking")
    b.status = payload.status
    db.commit()
    db.refresh(b)
    _audit(db, admin, "booking.update", "booking", b.id, status=b.status)
    return package_service.booking_out(b, db.get(User, b.user_id))


@router.delete("/package-bookings/{booking_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_booking(
    booking_id: uuid.UUID, admin: User = Depends(require_admin), db: Session = Depends(get_db),
) -> None:
    b = _get(db, PackageBooking, booking_id, "Booking")
    db.delete(b)
    db.commit()
    _audit(db, admin, "booking.delete", "booking", booking_id)


# --- businesses ------------------------------------------------------------------

@router.get("/businesses", response_model=Page[BusinessOut])
def admin_list_businesses(
    biz_status: str | None = Query(default=None, alias="status"), q: str = "",
    limit: int = 25, offset: int = 0, db: Session = Depends(get_db),
) -> Page[BusinessOut]:
    limit, offset = _page(limit, offset)
    where = []
    if biz_status == "blocked":
        where.append(User.is_blocked.is_(True))
    elif biz_status:
        where.append(BusinessProfile.status == biz_status)
    if q.strip():
        like = f"%{q.strip().lower()}%"
        where.append(or_(func.lower(BusinessProfile.business_name).like(like),
                         func.lower(BusinessProfile.city).like(like), func.lower(User.email).like(like)))
    base = select(BusinessProfile, User).join(User, User.id == BusinessProfile.user_id).where(*where)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = db.execute(base.order_by(BusinessProfile.created_at.desc()).limit(limit).offset(offset)).all()
    return Page(items=[business_service.to_out(db, p, u) for p, u in rows], total=total, limit=limit, offset=offset)


@router.put("/businesses/{user_id}", response_model=BusinessOut)
def admin_set_business_status(
    user_id: uuid.UUID, payload: BusinessStatusIn,
    admin: User = Depends(require_admin), db: Session = Depends(get_db),
) -> BusinessOut:
    p = _get(db, BusinessProfile, user_id, "Business")
    p.status = payload.status
    p.status_reason = (payload.reason or "").strip() or None
    p.reviewed_at = _now()
    db.commit()
    db.refresh(p)
    _audit(db, admin, f"business.{payload.status}", "business", p.user_id, title=p.business_name)
    return business_service.to_out(db, p)


@router.post("/businesses", response_model=BusinessOut, status_code=status.HTTP_201_CREATED)
def admin_create_business(
    payload: AdminBusinessCreate, admin: User = Depends(require_admin), db: Session = Depends(get_db),
) -> BusinessOut:
    """A merchant account made from the admin panel: the owner's login and the
    business profile together. No verification email is sent."""
    try:
        owner = user_service.create_user(
            db, name=payload.owner_name, email=payload.owner_email, password=payload.password,
            home_town=payload.city, phone=payload.business_phone,
        )
    except user_service.EmailAlreadyRegistered:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="An account with this email already exists") from None
    owner.role = "business"
    owner.is_verified = payload.is_verified
    p = BusinessProfile(
        user_id=owner.id, slug=business_service.unique_slug(db, payload.business_name),
        business_name=payload.business_name, city=payload.city, phone=payload.business_phone,
        status=payload.status, reviewed_at=_now(),
    )
    business_service.apply_fields(p, payload)
    db.add(p)
    db.commit()
    db.refresh(p)
    _audit(db, admin, "business.create", "business", p.user_id, title=p.business_name, email=owner.email)
    return business_service.to_out(db, p, owner)


@router.put("/businesses/{user_id}/profile", response_model=BusinessOut)
def admin_update_business(
    user_id: uuid.UUID, payload: BusinessUpdate,
    admin: User = Depends(require_admin), db: Session = Depends(get_db),
) -> BusinessOut:
    p = _get(db, BusinessProfile, user_id, "Business")
    if payload.business_name != p.business_name:
        p.slug = business_service.unique_slug(db, payload.business_name, keep_for=p.user_id)
    business_service.apply_fields(p, payload)
    db.commit()
    db.refresh(p)
    _audit(db, admin, "business.update", "business", p.user_id, title=p.business_name)
    return business_service.to_out(db, p)


@router.put("/businesses/{user_id}/block", response_model=BusinessOut)
def admin_block_business(
    user_id: uuid.UUID, payload: BusinessBlockIn,
    admin: User = Depends(require_admin), db: Session = Depends(get_db),
) -> BusinessOut:
    """Block: the owner is signed out everywhere and can't log in, and every
    package, the public page and new bookings disappear for travellers.
    Unblock puts it all back exactly as it was (status is left untouched)."""
    p = _get(db, BusinessProfile, user_id, "Business")
    owner = _get(db, User, user_id, "User")
    if owner.id == admin.id:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="You can't block your own account")
    owner.is_blocked = payload.blocked
    if payload.blocked:
        p.status_reason = (payload.reason or "").strip() or p.status_reason
    db.commit()
    if payload.blocked:
        session_service.revoke_all_for_user(db, owner.id, reason="admin")
    db.refresh(p)
    _audit(db, admin, "business.block" if payload.blocked else "business.unblock", "business", p.user_id,
           title=p.business_name, reason=payload.reason or "")
    return business_service.to_out(db, p, owner)
