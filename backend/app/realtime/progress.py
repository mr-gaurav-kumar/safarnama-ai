"""Progress events for a trip's itinerary generation, carried from wherever the
work runs to whoever is watching.

Two brokers with one interface:

  LocalBroker  -- TASK_BACKEND=inline. The job runs in this process (a thread in
                  FastAPI's pool), so an in-memory broker reaches the WebSocket.
  RedisBroker  -- TASK_BACKEND=celery. The job runs in a separate Celery worker,
                  and Redis pub/sub is the only thing both processes can see.

Every event carries a per-trip sequence number. A watcher that connects late
first receives the backlog, then live events; the sequence number lets it drop
anything it would otherwise see twice in the gap between the two.
"""
from __future__ import annotations

import asyncio
import json
import threading
import uuid
from collections import defaultdict, deque
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, Protocol

from app.core.config import settings

HISTORY_LIMIT = 50
HISTORY_TTL_SECONDS = 3600

Event = dict[str, Any]


def channel_for(trip_id: uuid.UUID | str) -> str:
    return f"trip:{trip_id}:progress"


class Broker(Protocol):
    def publish(self, channel: str, event: Event) -> Event: ...

    def subscribe(
        self, channel: str
    ) -> "AsyncIterator[tuple[list[Event], asyncio.Queue[Event]]]": ...


# --- in-process ---------------------------------------------------------------

class LocalBroker:
    """Thread-safe: `publish` is called from worker threads, `subscribe` from
    the event loop serving the WebSocket."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._seq: dict[str, int] = defaultdict(int)
        self._history: dict[str, deque[Event]] = defaultdict(
            lambda: deque(maxlen=HISTORY_LIMIT)
        )
        self._subscribers: dict[
            str, set[tuple[asyncio.AbstractEventLoop, asyncio.Queue[Event]]]
        ] = defaultdict(set)

    def publish(self, channel: str, event: Event) -> Event:
        with self._lock:
            self._seq[channel] += 1
            event = {**event, "seq": self._seq[channel]}
            self._history[channel].append(event)
            subscribers = list(self._subscribers[channel])

        for loop, queue in subscribers:
            # Hand the event to the loop that owns the queue; asyncio queues are
            # not safe to touch from another thread directly.
            loop.call_soon_threadsafe(queue.put_nowait, event)
        return event

    @asynccontextmanager
    async def subscribe(self, channel: str):
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[Event] = asyncio.Queue()
        entry = (loop, queue)
        with self._lock:
            self._subscribers[channel].add(entry)
            backlog = list(self._history[channel])
        try:
            yield backlog, queue
        finally:
            with self._lock:
                self._subscribers[channel].discard(entry)

    def reset(self) -> None:
        """Tests only."""
        with self._lock:
            self._seq.clear()
            self._history.clear()
            self._subscribers.clear()


# --- Redis --------------------------------------------------------------------

class RedisBroker:
    def __init__(self, url: str, *, client=None, async_client_factory=None) -> None:
        """`client` and `async_client_factory` exist for tests (fakeredis);
        normally both are built from `url`."""
        import redis
        import redis.asyncio as aioredis

        self._client = client or redis.Redis.from_url(url)
        self._async_client_factory = async_client_factory or (
            lambda: aioredis.Redis.from_url(url)
        )

    def publish(self, channel: str, event: Event) -> Event:
        seq = int(self._client.incr(f"{channel}:seq"))
        event = {**event, "seq": seq}
        payload = json.dumps(event)

        pipe = self._client.pipeline()
        pipe.expire(f"{channel}:seq", HISTORY_TTL_SECONDS)
        pipe.rpush(f"{channel}:history", payload)
        pipe.ltrim(f"{channel}:history", -HISTORY_LIMIT, -1)
        pipe.expire(f"{channel}:history", HISTORY_TTL_SECONDS)
        pipe.publish(channel, payload)
        pipe.execute()
        return event

    @asynccontextmanager
    async def subscribe(self, channel: str):
        client = self._async_client_factory()
        pubsub = client.pubsub()
        # Subscribe before reading the backlog: anything published in between
        # then arrives on both, and the sequence number removes the duplicate.
        # The other order would lose it.
        await pubsub.subscribe(channel)
        raw = await client.lrange(f"{channel}:history", 0, -1)
        backlog = [json.loads(r) for r in raw]

        queue: asyncio.Queue[Event] = asyncio.Queue()

        async def pump() -> None:
            async for message in pubsub.listen():
                if message.get("type") == "message":
                    await queue.put(json.loads(message["data"]))

        task = asyncio.create_task(pump())
        try:
            yield backlog, queue
        finally:
            task.cancel()
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()
            await client.aclose()


# --- selection ----------------------------------------------------------------

_broker: Broker | None = None
_broker_lock = threading.Lock()


def get_broker() -> Broker:
    global _broker
    if _broker is None:
        with _broker_lock:
            if _broker is None:
                _broker = (
                    RedisBroker(settings.REDIS_URL)
                    if settings.TASK_BACKEND == "celery"
                    else LocalBroker()
                )
    return _broker


# --- what the generation job calls ----------------------------------------------

def publish_progress(
    trip_id: uuid.UUID | str, step: str, message: str, thoughts: list[str] | None = None,
) -> None:
    event: Event = {"type": "progress", "step": step, "message": message}
    if thoughts:
        event["thoughts"] = thoughts
    get_broker().publish(channel_for(trip_id), event)


def publish_done(trip_id: uuid.UUID | str, status: str, error: str | None = None) -> None:
    get_broker().publish(
        channel_for(trip_id), {"type": "done", "status": status, "error": error}
    )
