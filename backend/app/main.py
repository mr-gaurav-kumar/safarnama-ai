"""FastAPI application entry point.

Routers are mounted here and nowhere else. Adding a feature means writing a
router module and adding one line to `_ROUTERS` below.
"""
import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.ratelimit_middleware import RateLimitMiddleware
from app.routers import admin, assistant, auth, bookings, business, chat, documents, geo, tickets, health, insights, media, packages, packing, rail, realtime, recommend, room, trips

logger = logging.getLogger(__name__)

REMINDER_CHECK_SECONDS = 6 * 3600


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """In inline mode, stand in for Celery Beat: check for trip reminders every
    few hours. Running often is safe -- each reminder is sent once."""
    scheduler_task: asyncio.Task[None] | None = None
    if settings.TASK_BACKEND == "inline" and settings.SCHEDULER_ENABLED:
        from app.tasks import jobs
        from app.tasks.scheduler import run_periodically

        scheduler_task = asyncio.create_task(
            run_periodically(jobs.send_trip_reminders, every_seconds=REMINDER_CHECK_SECONDS)
        )
    logger.info("Background jobs: %s", settings.TASK_BACKEND)
    yield
    if scheduler_task is not None:
        scheduler_task.cancel()


app = FastAPI(
    title=settings.APP_NAME,
    version="0.3.0",
    docs_url="/docs",
    lifespan=lifespan,
)

# Added before CORS so CORS wraps it: a 429 still carries CORS headers and the
# browser shows the real error instead of a CORS failure.
app.add_middleware(RateLimitMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_ROUTERS = (
    health.router,
    auth.router,
    documents.router,
    tickets.router,
    trips.router,
    trips.invitations_router,
    packing.router,
    packing.admin_router,
    realtime.router,
    room.router,
    chat.router,
    bookings.router,
    insights.router,
    geo.router,
    packages.router,
    business.router,
    business.public_router,
    media.router,
    rail.router,
    recommend.router,
    assistant.router,
    admin.router,
)

for router in _ROUTERS:
    app.include_router(router)

# Uploaded package photos. Created on start so the mount never fails on a
# fresh checkout.
settings.MEDIA_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=settings.MEDIA_DIR), name="media")


@app.get("/", tags=["meta"])
def root() -> dict[str, str]:
    return {"app": settings.APP_NAME, "docs": "/docs", "health": "/health"}
