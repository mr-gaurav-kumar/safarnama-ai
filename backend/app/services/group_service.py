"""Who may do what on a trip, and group-trip actions (§4.10).

Roles
  owner   -- created the trip (trips.user_id)
  member  -- accepted an invitation (trip_collaborators.status = 'joined')

                       owner  member
  view trip / PDF        yes    yes
  email me the PDF       yes    yes   (to their own verified address)
  trip room              yes    yes
  own preferences        yes    yes
  rate after the trip    yes    yes
  invite / remove        yes    -
  replan / delete        yes    -
  leave                  -      yes

Anyone else gets "not found" -- the same answer as for a trip that does not
exist, so trip ids cannot be probed.
"""
from __future__ import annotations

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Literal

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.group import TripCollaborator, TripFeedback, TripMatchRequest
from app.models.trip import Trip
from app.models.user import User

Role = Literal["owner", "member"]

MAX_MEMBERS = 10           # invited + joined, not counting the owner
MATCH_REQUESTS_PER_DAY = 5


class TripNotFound(Exception):
    pass


class Forbidden(Exception):
    """Can see the trip, but not do this to it (a member trying an owner action)."""


class GroupError(Exception):
    """A request that makes sense but cannot be done -- the message says why."""


def _hash(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# --- access -------------------------------------------------------------------

def role_on(db: Session, user_id: uuid.UUID, trip: Trip) -> Role | None:
    if trip.user_id == user_id:
        return "owner"
    joined = db.scalar(
        select(TripCollaborator.id).where(
            TripCollaborator.trip_id == trip.id,
            TripCollaborator.user_id == user_id,
            TripCollaborator.status == "joined",
        )
    )
    return "member" if joined else None


def trip_for(
    db: Session, user_id: uuid.UUID, trip_id: uuid.UUID, *, owner_only: bool = False
) -> tuple[Trip, Role]:
    trip = db.scalar(
        select(Trip).where(Trip.id == trip_id).options(selectinload(Trip.itinerary))
    )
    role = role_on(db, user_id, trip) if trip is not None else None
    if trip is None or role is None:
        raise TripNotFound(str(trip_id))
    if owner_only and role != "owner":
        raise Forbidden("Only the trip's organiser can do this")
    return trip, role


@dataclass
class TripListing:
    trip: Trip
    role: Role
    member_count: int
    my_rating: int | None


def list_for_user(db: Session, user_id: uuid.UUID) -> list[TripListing]:
    member_trip_ids = select(TripCollaborator.trip_id).where(
        TripCollaborator.user_id == user_id, TripCollaborator.status == "joined"
    )
    trips = db.scalars(
        select(Trip)
        .where(or_(Trip.user_id == user_id, Trip.id.in_(member_trip_ids)))
        .order_by(Trip.created_at.desc())
    ).all()
    if not trips:
        return []
    ids = [t.id for t in trips]

    counts = dict(db.execute(
        select(TripCollaborator.trip_id, func.count())
        .where(TripCollaborator.trip_id.in_(ids), TripCollaborator.status == "joined")
        .group_by(TripCollaborator.trip_id)
    ).all())
    ratings = dict(db.execute(
        select(TripFeedback.trip_id, TripFeedback.rating)
        .where(TripFeedback.trip_id.in_(ids), TripFeedback.user_id == user_id)
    ).all())
    return [
        TripListing(
            trip=t,
            role="owner" if t.user_id == user_id else "member",
            member_count=counts.get(t.id, 0),
            my_rating=ratings.get(t.id),
        )
        for t in trips
    ]


# --- members ------------------------------------------------------------------

@dataclass
class MemberView:
    id: str | None          # collaborator id; None for the owner
    name: str | None        # None until they join -- an invite shows only the address
    email: str
    role: Literal["owner", "member", "invited", "declined"]
    style_tags: list[str]
    is_you: bool


def members(db: Session, trip: Trip, viewer_id: uuid.UUID, viewer_role: Role) -> list[MemberView]:
    owner = db.get(User, trip.user_id)
    out = [MemberView(
        id=None, name=owner.name, email=owner.email, role="owner",
        style_tags=list(trip.style_tags), is_you=owner.id == viewer_id,
    )]
    rows = db.scalars(
        select(TripCollaborator).where(TripCollaborator.trip_id == trip.id)
        .order_by(TripCollaborator.created_at)
    ).all()
    for c in rows:
        # Members see who is in the group; only the organiser sees pending and
        # declined invitations (someone declining is not everyone's business).
        if c.status != "joined" and viewer_role != "owner":
            continue
        user = db.get(User, c.user_id) if c.user_id else None
        out.append(MemberView(
            id=str(c.id),
            name=user.name if user else None,
            email=c.invited_email,
            role="member" if c.status == "joined" else c.status,  # type: ignore[arg-type]
            style_tags=list(c.style_tags) if c.status == "joined" else [],
            is_you=c.user_id == viewer_id,
        ))
    return out


def invite(db: Session, trip: Trip, owner: User, email: str) -> tuple[TripCollaborator, str]:
    """Returns the row and the raw token for the join link (emailed, never stored)."""
    email = email.strip().lower()
    if email == owner.email:
        raise GroupError("You are already on this trip")

    existing = db.scalar(
        select(TripCollaborator).where(
            TripCollaborator.trip_id == trip.id, TripCollaborator.invited_email == email
        )
    )
    if existing is not None and existing.status == "joined":
        raise GroupError("They have already joined this trip")

    if existing is None:
        active = db.scalar(
            select(func.count()).select_from(TripCollaborator).where(
                TripCollaborator.trip_id == trip.id, TripCollaborator.status != "declined"
            )
        ) or 0
        if active >= MAX_MEMBERS:
            raise GroupError(f"A trip can have at most {MAX_MEMBERS} people besides you")

    raw = secrets.token_urlsafe(32)
    if existing is None:
        existing = TripCollaborator(
            trip_id=trip.id, invited_email=email, invited_by=owner.id, style_tags=[],
            invite_token_hash=_hash(raw), status="invited",
        )
        db.add(existing)
    else:
        # Re-inviting (after a decline, or to resend): a fresh link, old one dead.
        existing.invite_token_hash = _hash(raw)
        existing.status = "invited"
        existing.invited_by = owner.id
    db.commit()
    db.refresh(existing)
    return existing, raw


def _require_verified(user: User) -> None:
    # Otherwise anyone could sign up with the invitee's address -- without
    # being able to read its inbox -- and take their place on the trip.
    if not user.is_verified:
        raise GroupError("Confirm your email address first, then open the invitation again")


def _invitation(db: Session, user: User, trip_id: uuid.UUID, token: str | None) -> TripCollaborator:
    _require_verified(user)
    query = select(TripCollaborator).where(
        TripCollaborator.trip_id == trip_id, TripCollaborator.invited_email == user.email
    )
    if token is not None:
        query = query.where(TripCollaborator.invite_token_hash == _hash(token))
    row = db.scalar(query)
    if row is None:
        raise TripNotFound(str(trip_id))
    return row


def join(db: Session, user: User, trip_id: uuid.UUID, token: str | None = None) -> TripCollaborator:
    """With a token (from the email link) or without (from the dashboard's
    invitations list) -- either way only for the address that was invited."""
    row = _invitation(db, user, trip_id, token)
    if row.status == "joined":
        return row
    trip = db.get(Trip, trip_id)
    if trip is None or trip.user_id == user.id:
        raise TripNotFound(str(trip_id))
    row.status = "joined"
    row.user_id = user.id
    row.joined_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return row


def decline(db: Session, user: User, trip_id: uuid.UUID, token: str | None = None) -> None:
    row = _invitation(db, user, trip_id, token)
    if row.status == "joined":
        raise GroupError("You have already joined -- leave the trip instead")
    row.status = "declined"
    db.commit()


def pending_invitations(db: Session, user: User) -> list[tuple[TripCollaborator, Trip, User]]:
    if not user.is_verified:
        return []
    rows = db.execute(
        select(TripCollaborator, Trip, User)
        .join(Trip, Trip.id == TripCollaborator.trip_id)
        .join(User, User.id == Trip.user_id)
        .where(TripCollaborator.invited_email == user.email, TripCollaborator.status == "invited")
        .order_by(TripCollaborator.created_at.desc())
    ).all()
    return [(c, t, u) for c, t, u in rows]


def leave(db: Session, user: User, trip_id: uuid.UUID) -> None:
    trip, role = trip_for(db, user.id, trip_id)
    if role == "owner":
        raise GroupError("You organise this trip -- delete it instead of leaving")
    row = db.scalar(select(TripCollaborator).where(
        TripCollaborator.trip_id == trip.id, TripCollaborator.user_id == user.id
    ))
    db.delete(row)
    db.commit()


def remove(db: Session, owner: User, trip_id: uuid.UUID, collaborator_id: uuid.UUID) -> None:
    trip, _ = trip_for(db, owner.id, trip_id, owner_only=True)
    row = db.get(TripCollaborator, collaborator_id)
    if row is None or row.trip_id != trip.id:
        raise TripNotFound(str(collaborator_id))
    db.delete(row)
    db.commit()


def set_my_preferences(db: Session, user: User, trip_id: uuid.UUID, tags: list[str]) -> None:
    trip, role = trip_for(db, user.id, trip_id)
    if role == "owner":
        trip.style_tags = list(tags)
    else:
        row = db.scalar(select(TripCollaborator).where(
            TripCollaborator.trip_id == trip.id, TripCollaborator.user_id == user.id
        ))
        row.style_tags = list(tags)
    db.commit()


# --- planning for a group -----------------------------------------------------

@dataclass(frozen=True)
class GroupPreferences:
    tags: list[str]            # every tag anyone wants, most-wanted first
    context: str | None        # one line for the planner; None for a solo trip


def group_preferences(db: Session, trip: Trip) -> GroupPreferences:
    owner = db.get(User, trip.user_id)
    people: list[tuple[str, list[str]]] = [(owner.name.split()[0], list(trip.style_tags))]
    for c, u in db.execute(
        select(TripCollaborator, User).join(User, User.id == TripCollaborator.user_id)
        .where(TripCollaborator.trip_id == trip.id, TripCollaborator.status == "joined")
        .order_by(TripCollaborator.joined_at)
    ).all():
        people.append((u.name.split()[0], list(c.style_tags)))

    counts: dict[str, int] = {}
    for _, tags in people:
        for tag in tags:
            counts[tag] = counts.get(tag, 0) + 1
    # Most-wanted first; ties keep first-mentioned order (dicts are ordered).
    merged = sorted(counts, key=lambda t: -counts[t])

    if len(people) == 1:
        return GroupPreferences(tags=merged, context=None)

    wants = "; ".join(
        f"{name} wants {', '.join(tags)}" if tags else f"{name} has no preference"
        for name, tags in people
    )
    return GroupPreferences(
        tags=merged,
        context=(f"This is a group of {len(people)} planning together. {wants}. "
                 "Balance the days so everyone gets something they asked for, and "
                 "say in the explanation how you balanced it."),
    )


# --- finding other travellers (opt-in) --------------------------------------------

@dataclass
class Match:
    trip_id: str
    first_name: str
    start_date: date
    end_date: date
    overlap_days: int
    already_requested: bool


def _same_place(a: str, b: str) -> bool:
    return " ".join(a.lower().split()) == " ".join(b.lower().split())


def matches(db: Session, user: User, trip_id: uuid.UUID) -> list[Match]:
    trip, _ = trip_for(db, user.id, trip_id, owner_only=True)
    # Reciprocal: you only see others if they can see you.
    if not trip.discoverable:
        return []
    candidates = db.execute(
        select(Trip, User).join(User, User.id == Trip.user_id).where(
            Trip.discoverable.is_(True),
            Trip.user_id != user.id,
            Trip.start_date <= trip.end_date,
            Trip.end_date >= trip.start_date,
            Trip.end_date >= date.today(),
            User.is_blocked.is_(False),
        )
    ).all()
    requested = set(db.scalars(
        select(TripMatchRequest.to_trip_id).where(TripMatchRequest.from_trip_id == trip.id)
    ))
    out = []
    for other, owner in candidates:
        if not _same_place(other.destination, trip.destination):
            continue
        overlap = (min(other.end_date, trip.end_date) - max(other.start_date, trip.start_date)).days + 1
        out.append(Match(
            trip_id=str(other.id), first_name=owner.name.split()[0],
            start_date=other.start_date, end_date=other.end_date,
            overlap_days=overlap, already_requested=other.id in requested,
        ))
    out.sort(key=lambda m: -m.overlap_days)
    return out


def request_match(db: Session, user: User, trip_id: uuid.UUID, other_trip_id: uuid.UUID) -> tuple[Trip, User]:
    """Returns (their trip, its owner) for the notification email."""
    _require_verified(user)
    if not any(m.trip_id == str(other_trip_id) for m in matches(db, user, trip_id)):
        raise TripNotFound(str(other_trip_id))

    exists = db.scalar(select(TripMatchRequest.id).where(
        TripMatchRequest.from_trip_id == trip_id, TripMatchRequest.to_trip_id == other_trip_id
    ))
    if exists:
        raise GroupError("You have already suggested teaming up with this traveller")

    today = db.scalar(
        select(func.count()).select_from(TripMatchRequest).where(
            TripMatchRequest.from_user_id == user.id,
            TripMatchRequest.created_at >= datetime.now(timezone.utc) - timedelta(days=1),
        )
    ) or 0
    if today >= MATCH_REQUESTS_PER_DAY:
        raise GroupError(f"You can suggest teaming up at most {MATCH_REQUESTS_PER_DAY} times a day")

    db.add(TripMatchRequest(from_trip_id=trip_id, to_trip_id=other_trip_id, from_user_id=user.id))
    db.commit()
    other = db.get(Trip, other_trip_id)
    return other, db.get(User, other.user_id)
