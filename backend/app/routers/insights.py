"""GET /insights -- official tourism statistics for the Insights dashboard.

Public: it is government data and contains nothing about any user.
"""
from fastapi import APIRouter, Response

from app.data.tourism import insights_payload

router = APIRouter(prefix="/insights", tags=["insights"])


@router.get("")
def insights(response: Response) -> dict:
    # A dated snapshot that changes once a year at most.
    response.headers["Cache-Control"] = "public, max-age=86400"
    return insights_payload()
