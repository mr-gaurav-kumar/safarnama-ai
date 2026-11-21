"""Trip endpoints -- §4.2-4.5, §4.10-4.11 and §6 of the project document.

Access is decided in app/services/group_service.py: the owner and joined members
can see a trip; only the owner can change who is on it, replan or delete it.
"""
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.export.pdf import filename_for, render_itinerary_pdf
from app.fraud import events
from app.models.trip import Trip
from app.models.user import User
from app.schemas.group import (
    DiscoverableRequest, FeedbackRequest, FeedbackSummary, InviteRequest, InvitationOut,
    JoinRequest, MatchOut, MemberOut, PreferencesRequest,
)
from app.schemas.trip import CopyRequest, OwnPlanCreate, PlanUpdate, TripCreate, TripDetail, TripRead
from app.services import feedback_service, group_service, own_plan, trip_service
from app.services.group_service import Forbidden, GroupError, TripNotFound
from app.tasks import jobs
from app.tasks.dispatch import enqueue

router = APIRouter(prefix="/trips", tags=["trips"])
invitations_router = APIRouter(prefix="/invitations", tags=["trips"])

_NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")


def _load(db: Session, user: User, trip_id: uuid.UUID, *, owner_only: bool = False):
    try:
        return group_service.trip_for(db, user.id, trip_id, owner_only=owner_only)
    except TripNotFound:
        raise _NOT_FOUND from None
    except Forbidden as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(exc)) from None


def _conflict(exc: Exception) -> HTTPException:
    return HTTPException(status.HTTP_409_CONFLICT, detail=str(exc))


def _detail(trip: Trip, role: str) -> TripDetail:
    out = TripDetail.model_validate(trip)
    out.role = role  # type: ignore[assignment]
    return out


# --- trips --------------------------------------------------------------------

@router.get("", response_model=list[TripRead])
def list_trips(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[TripRead]:
    """Your trips and the ones you have joined, newest first."""
    out = []
    for item in group_service.list_for_user(db, user.id):
        row = TripRead.model_validate(item.trip)
        row.role = item.role
        row.member_count = item.member_count
        row.my_rating = item.my_rating
        out.append(row)
    return out


@router.post("", response_model=TripDetail, status_code=status.HTTP_202_ACCEPTED)
def create_trip(
    payload: TripCreate,
    background: BackgroundTasks,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TripDetail:
    """Accept a trip request and return at once with status 'processing'.

    202, not 201: the trip exists, but its itinerary does not yet. The client
    follows WS /ws/trips/{id} for live progress, or polls GET /trips/{id}.
    """
    trip = trip_service.create_trip(db, user_id=user.id, payload=payload)
    enqueue(background, jobs.run_trip_generation, str(trip.id))
    _track(db, background, request, user, "trip_created", trip.id)
    return _detail(trip, "owner")


@router.post("/own", response_model=TripDetail, status_code=status.HTTP_201_CREATED)
def create_own_plan(
    payload: OwnPlanCreate, background: BackgroundTasks, request: Request,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
) -> TripDetail:
    """Save a plan the traveller wrote themselves. No AI: it is ready at once."""
    trip = own_plan.create_own_plan(db, user_id=user.id, payload=payload)
    enqueue(background, jobs.enrich_saved_plan, str(trip.id))
    _track(db, background, request, user, "trip_created", trip.id)
    return _detail(trip, "owner")


@router.post("/own/fill")
def fill_own_plan(payload: OwnPlanCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    """Fill the gaps in a plan the traveller is writing: activities for empty
    days, blank times/places/costs, packing items. Nothing is saved; the
    traveller's own entries always come back unchanged."""
    from app.core import ratelimit
    from app.core.config import settings
    from app.llm import plan_fill

    if settings.RATE_LIMIT_ENABLED:
        allowed, retry = ratelimit.check("plan-fill", str(user.id), limit=6, window_seconds=60)
        if not allowed:
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, detail=f"Too many at once — try again in {retry}s.")
    return plan_fill.fill(db, payload)


@router.put("/{trip_id}/plan", response_model=TripDetail)
def edit_plan(
    trip_id: uuid.UUID, payload: PlanUpdate, background: BackgroundTasks,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
) -> TripDetail:
    """Change the days of a plan -- the traveller's own or the AI's."""
    trip, role = _load(db, user, trip_id, owner_only=True)
    if trip.status == "processing":
        raise _conflict(GroupError("This trip is still being planned"))
    trip = own_plan.replace_days(db, trip, payload.days, payload.notes, payload.packing, user.id)
    enqueue(background, jobs.enrich_saved_plan, str(trip.id))
    return _detail(trip, role)


@router.post("/{trip_id}/copy", response_model=TripDetail, status_code=status.HTTP_201_CREATED)
def copy_trip(
    trip_id: uuid.UUID, payload: CopyRequest, background: BackgroundTasks, request: Request,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
) -> TripDetail:
    """Plan this trip again on new dates. The copy is yours, even if you were a member."""
    trip, _ = _load(db, user, trip_id)
    if trip.status != "completed" or trip.itinerary is None:
        raise _conflict(GroupError("Only a finished plan can be planned again"))
    new = own_plan.copy_trip(db, trip, user_id=user.id, start=payload.start_date)
    enqueue(background, jobs.enrich_saved_plan, str(new.id))
    _track(db, background, request, user, "trip_created", new.id)
    return _detail(new, "owner")


@router.get("/{trip_id}", response_model=TripDetail)
def get_trip(trip_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> TripDetail:
    trip, role = _load(db, user, trip_id)
    return _detail(trip, role)


@router.delete("/{trip_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_trip(trip_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> None:
    trip, _ = _load(db, user, trip_id, owner_only=True)
    db.delete(trip)
    db.commit()


@router.post("/{trip_id}/replan", response_model=TripDetail, status_code=status.HTTP_202_ACCEPTED)
def replan(
    trip_id: uuid.UUID,
    background: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TripDetail:
    """Plan again -- e.g. after members joined or changed what they want."""
    trip, role = _load(db, user, trip_id, owner_only=True)
    if trip.status == "processing":
        raise _conflict(GroupError("This trip is already being planned"))
    trip.status = "processing"
    trip.error = None
    trip.source = "ai"  # a plan the traveller wrote can be handed to the planner
    db.commit()
    enqueue(background, jobs.run_trip_generation, str(trip.id))
    return _detail(trip, role)


@router.put("/{trip_id}/discoverable", response_model=TripDetail)
def set_discoverable(
    trip_id: uuid.UUID, payload: DiscoverableRequest,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
) -> TripDetail:
    trip, role = _load(db, user, trip_id, owner_only=True)
    trip.discoverable = payload.discoverable
    db.commit()
    return _detail(trip, role)


# --- export ---------------------------------------------------------------------

def _completed(db: Session, user: User, trip_id: uuid.UUID) -> Trip:
    trip, _ = _load(db, user, trip_id)
    if trip.status != "completed" or trip.itinerary is None:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="This trip's plan is not ready yet")
    return trip


@router.get("/{trip_id}/pdf", response_class=Response, responses={200: {"content": {"application/pdf": {}}}})
def download_pdf(trip_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Response:
    trip = _completed(db, user, trip_id)
    return Response(
        content=render_itinerary_pdf(trip, db=db, user_id=user.id),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename_for(trip)}"'},
    )


@router.post("/{trip_id}/email", status_code=status.HTTP_202_ACCEPTED)
def email_itinerary(
    trip_id: uuid.UUID, background: BackgroundTasks,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
) -> dict[str, str]:
    _completed(db, user, trip_id)
    if not user.is_verified:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Confirm your email address first -- we only send to verified addresses",
        )
    enqueue(background, jobs.send_itinerary_copy_email, str(trip_id), str(user.id))
    return {"detail": f"Sending the itinerary to {user.email}"}


# --- group ------------------------------------------------------------------------

@router.get("/{trip_id}/members", response_model=list[MemberOut])
def list_members(trip_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[MemberOut]:
    trip, role = _load(db, user, trip_id)
    return [MemberOut(**m.__dict__) for m in group_service.members(db, trip, user.id, role)]


@router.post("/{trip_id}/invite", status_code=status.HTTP_202_ACCEPTED)
def invite(
    trip_id: uuid.UUID, payload: InviteRequest, background: BackgroundTasks, request: Request,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
) -> dict[str, str]:
    trip, _ = _load(db, user, trip_id, owner_only=True)
    try:
        row, token = group_service.invite(db, trip, user, payload.email)
    except GroupError as exc:
        raise _conflict(exc) from None
    enqueue(background, jobs.send_trip_invitation, str(row.id), token)
    _track(db, background, request, user, "invite_sent", trip.id)
    _room_event(trip.id)
    return {"detail": f"Invitation sent to {row.invited_email}"}


@router.post("/{trip_id}/join", response_model=TripDetail)
def join(
    trip_id: uuid.UUID, payload: JoinRequest,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
) -> TripDetail:
    try:
        group_service.join(db, user, trip_id, payload.token)
    except TripNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND,
                            detail="This invitation isn't for this account, or is no longer valid") from None
    except GroupError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(exc)) from None
    _room_event(trip_id)
    trip, role = _load(db, user, trip_id)
    return _detail(trip, role)


@router.post("/{trip_id}/decline", status_code=status.HTTP_204_NO_CONTENT)
def decline(
    trip_id: uuid.UUID, payload: JoinRequest,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
) -> None:
    try:
        group_service.decline(db, user, trip_id, payload.token)
    except TripNotFound:
        raise _NOT_FOUND from None
    except GroupError as exc:
        raise _conflict(exc) from None


@router.post("/{trip_id}/leave", status_code=status.HTTP_204_NO_CONTENT)
def leave(trip_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> None:
    try:
        group_service.leave(db, user, trip_id)
    except TripNotFound:
        raise _NOT_FOUND from None
    except GroupError as exc:
        raise _conflict(exc) from None
    _room_event(trip_id)


@router.delete("/{trip_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    trip_id: uuid.UUID, member_id: uuid.UUID,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
) -> None:
    try:
        group_service.remove(db, user, trip_id, member_id)
    except TripNotFound:
        raise _NOT_FOUND from None
    except Forbidden as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(exc)) from None
    _room_event(trip_id)


@router.put("/{trip_id}/my-preferences", status_code=status.HTTP_204_NO_CONTENT)
def my_preferences(
    trip_id: uuid.UUID, payload: PreferencesRequest,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
) -> None:
    try:
        group_service.set_my_preferences(db, user, trip_id, list(payload.style_tags))
    except TripNotFound:
        raise _NOT_FOUND from None
    _room_event(trip_id)


@router.get("/{trip_id}/matches", response_model=list[MatchOut])
def matches(trip_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[MatchOut]:
    try:
        return [MatchOut(**m.__dict__) for m in group_service.matches(db, user, trip_id)]
    except TripNotFound:
        raise _NOT_FOUND from None
    except Forbidden as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(exc)) from None


@router.post("/{trip_id}/matches/{other_trip_id}/request", status_code=status.HTTP_202_ACCEPTED)
def request_match(
    trip_id: uuid.UUID, other_trip_id: uuid.UUID, background: BackgroundTasks, request: Request,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
) -> dict[str, str]:
    """Shares your first name and email with the other traveller -- the UI says
    so on the button."""
    try:
        other, owner = group_service.request_match(db, user, trip_id, other_trip_id)
    except (TripNotFound, Forbidden):
        raise _NOT_FOUND from None
    except GroupError as exc:
        raise _conflict(exc) from None
    enqueue(background, jobs.send_match_request, str(trip_id), str(other_trip_id))
    _track(db, background, request, user, "match_request", trip_id)
    return {"detail": f"We've let {owner.name.split()[0]} know"}


# --- feedback -----------------------------------------------------------------------

@router.get("/{trip_id}/feedback", response_model=FeedbackSummary)
def get_feedback(trip_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    try:
        return feedback_service.summary(db, user, trip_id)
    except TripNotFound:
        raise _NOT_FOUND from None


@router.put("/{trip_id}/feedback", response_model=FeedbackSummary)
def rate(
    trip_id: uuid.UUID, payload: FeedbackRequest,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
) -> dict:
    try:
        feedback_service.rate(db, user, trip_id, payload.rating, payload.comment)
    except TripNotFound:
        raise _NOT_FOUND from None
    except GroupError as exc:
        raise _conflict(exc) from None
    return feedback_service.summary(db, user, trip_id)


# --- invitations for the current user ------------------------------------------------

@invitations_router.get("", response_model=list[InvitationOut])
def my_invitations(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[InvitationOut]:
    return [
        InvitationOut(
            trip_id=str(t.id), destination=t.destination, start_date=t.start_date,
            end_date=t.end_date, invited_by=owner.name,
        )
        for _, t, owner in group_service.pending_invitations(db, user)
    ]


def _track(db: Session, background: BackgroundTasks, request: Request, user: User,
           kind: str, trip_id: uuid.UUID) -> None:
    """Record the event now; score it for fraud in the background."""
    ip = events.client_ip(request)
    events.record(db, kind, user_id=user.id, ip=ip, trip_id=trip_id)
    enqueue(background, jobs.score_activity, str(user.id), ip or "")


def _room_event(trip_id: uuid.UUID) -> None:
    """Tell anyone in the trip room that the member list changed."""
    from app.realtime.progress import get_broker

    try:
        get_broker().publish(f"trip:{trip_id}:room", {"type": "members_changed"})
    except Exception:  # noqa: BLE001 -- a missed refresh is harmless
        pass
