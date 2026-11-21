"""Phase 8: the budget recommender and a preview of Think on the Plan."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.ml.budget_recommender import recommend
from app.ml.think import think_about_trip
from app.models.user import User
from app.schemas.recommend import BudgetRequest, BudgetResponse, ThinkRequest, ThinkResponse

router = APIRouter(prefix="/recommend", tags=["recommend"])

# "To: Manali" also shows places this close to Manali.
NEAR_KM = 250


@router.post("/budget", response_model=BudgetResponse)
def budget_recommendations(
    payload: BudgetRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db),
) -> dict:
    """Where can this budget go? Ranked destinations, each with its reasons.

    With `origin`, every place is priced from where the traveller starts;
    with `destination`, the list is narrowed to that place and its
    neighbours, or to that state."""
    from app.assistant.estimate import distance_km
    from app.assistant.service import _origin_point, find_place
    from app.ml.features import all_destinations

    rows = all_destinations(db)
    origin_name = (payload.origin or "").strip() or (user.home_town or "")
    point, label = _origin_point(db, rows, origin_name) if origin_name else (None, None)

    only = anchor = mode = note = None
    want = (payload.destination or "").strip()
    if want:
        place = find_place(rows, want.split(",")[0])
        state = want.split(",")[-1].strip().lower() if place is None else ""
        in_state = {r.name for r in rows if state and len(state) >= 4 and (state in r.state.lower() or r.state.lower() in state)}
        if place is not None:
            anchor, mode = place.name, "place"
            only = {r.name for r in rows if distance_km((place.lat, place.lng), (r.lat, r.lng)) <= NEAR_KM}
            note = f"{place.name} and places within about {NEAR_KM} km of it"
        elif in_state:
            only, mode = in_state, "state"
            note = f"Places in {next(r.state for r in rows if r.name in in_state)}"
        else:
            mode, note = "not_found", f"We don't know “{want}” yet, so here is everywhere that fits"

    result = recommend(
        db, budget=float(payload.budget), days=payload.days, travelers=payload.travelers,
        style_tags=list(payload.style_tags), month=payload.month,
        user_id=user.id if payload.use_memory else None, limit=payload.limit,
        origin=point, only=only, anchor=anchor,
    )
    result.update(origin=label or (origin_name or None), origin_found=point is not None,
                  destination_mode=mode, destination_note=note)
    return result


@router.post("/think", response_model=ThinkResponse)
def think_preview(
    payload: ThinkRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db),
) -> dict:
    """What the planner would think about this trip -- without planning it."""
    return think_about_trip(
        db, destination=payload.destination, start_date=payload.start_date,
        end_date=payload.end_date, budget=float(payload.budget),
        travelers=payload.travelers, style_tags=list(payload.style_tags),
    )
