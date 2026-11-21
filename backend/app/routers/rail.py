"""GET /rail/... -- live train search (optional; needs RAPIDAPI_KEY)."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.deps import get_current_user
from app.models.user import User
from app.rail import irctc

router = APIRouter(prefix="/rail", tags=["rail"])

_NOT_SET = HTTPException(
    status.HTTP_503_SERVICE_UNAVAILABLE,
    detail="Live train search is not set up. Add RAPIDAPI_KEY to .env to turn it on.",
)


@router.get("/status")
def rail_status() -> dict:
    return {"live_search": irctc.configured()}


# Signed-in users only: the free quota is small and shared by everyone.
@router.get("/stations")
def stations(q: str = Query(min_length=2, max_length=60), _: User = Depends(get_current_user)) -> list[dict]:
    try:
        return irctc.search_stations(q)[:10]
    except irctc.RailNotConfigured:
        raise _NOT_SET from None
    except irctc.RailUnavailable as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from None


@router.get("/trains")
def trains(
    src: str = Query(alias="from", min_length=2, max_length=6, pattern=r"^[A-Za-z]+$"),
    dst: str = Query(alias="to", min_length=2, max_length=6, pattern=r"^[A-Za-z]+$"),
    day: date = Query(alias="date"),
    _: User = Depends(get_current_user),
) -> dict:
    if src.upper() == dst.upper():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="From and To must be different stations")
    if day < date.today():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Pick today or a later date")
    try:
        rows = irctc.trains_between(src, dst, day)
    except irctc.RailNotConfigured:
        raise _NOT_SET from None
    except irctc.RailUnavailable as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from None
    return {"from": src.upper(), "to": dst.upper(), "date": day.isoformat(), "trains": rows}
