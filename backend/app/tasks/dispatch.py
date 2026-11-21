"""Run a job in the background -- in this process, or on a Celery worker.

    enqueue(background_tasks, jobs.run_trip_generation, str(trip.id))

TASK_BACKEND=inline  FastAPI runs the job after the response is sent, in its
                     thread pool. No Redis, no worker process.
TASK_BACKEND=celery  The job goes onto the Redis queue for a Celery worker.

Callers never know which; switching is one line in .env.
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from fastapi import BackgroundTasks

from app.core.config import settings

logger = logging.getLogger(__name__)

Job = Callable[..., Any]


def enqueue(background: BackgroundTasks | None, job: Job, *args: str) -> None:
    if settings.TASK_BACKEND == "celery":
        from app.tasks.celery_app import task_for

        task_for(job).delay(*args)
        return

    if background is not None:
        background.add_task(_run_safely, job, *args)
    else:
        # Already inside a background job (e.g. generation queueing its email):
        # just run it.
        _run_safely(job, *args)


def _run_safely(job: Job, *args: str) -> None:
    """Inline jobs run after the response has gone, so an exception has nowhere
    useful to go. Log it with the job's name instead of a bare traceback."""
    try:
        job(*args)
    except Exception:  # noqa: BLE001
        logger.exception("Background job %s%s failed", job.__name__, args)
