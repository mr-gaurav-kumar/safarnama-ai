"""Liveness + readiness. The hosting platform points its health check here."""
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.database import get_db

router = APIRouter(tags=["meta"])


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness: the process is up. Never touches the database."""
    return {"status": "ok"}


@router.get("/health/db")
def health_db(db: Session = Depends(get_db)) -> JSONResponse:
    """Readiness: Postgres answers and the pgvector extension is installed.

    Returns 503 rather than a traceback when the database is unreachable, so a
    platform health check reads it as 'not ready' instead of 'crashed'.
    """
    try:
        db.execute(text("SELECT 1"))
        has_vector = db.execute(
            text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')")
        ).scalar()
    except SQLAlchemyError as exc:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unavailable",
                "database": "unreachable",
                "hint": "Is Postgres running, and does DATABASE_URL in .env match it?",
                "error": type(exc).__name__,
            },
        )

    if not has_vector:
        return JSONResponse(
            status_code=503,
            content={
                "status": "degraded",
                "database": "ok",
                "pgvector": False,
                "hint": "Run: alembic upgrade head",
            },
        )

    return JSONResponse(content={"status": "ok", "database": "ok", "pgvector": True})
