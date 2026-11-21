"""A tiny in-process scheduler for TASK_BACKEND=inline, standing in for Celery
Beat so reminders still go out on a laptop with no worker running."""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import Any

from starlette.concurrency import run_in_threadpool

logger = logging.getLogger(__name__)


async def run_periodically(
    job: Callable[[], Any], *, every_seconds: float, first_delay: float = 30
) -> None:
    await asyncio.sleep(first_delay)
    while True:
        try:
            # The job does blocking I/O (database, SMTP); keep it off the loop.
            await run_in_threadpool(job)
        except Exception:  # noqa: BLE001 -- one bad run must not stop the schedule
            logger.exception("Scheduled job %s failed", getattr(job, "__name__", job))
        await asyncio.sleep(every_seconds)
