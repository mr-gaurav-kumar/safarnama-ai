"""WS /ws/trips/{id}: who may watch, and what they see."""
import pytest
from starlette.websockets import WebSocketDisconnect

from app.realtime import progress
from tests.helpers import OTHER, SIGNUP, create_trip, signup

TRIP = {
    "destination": "Goa", "start_date": "2026-10-01", "end_date": "2026-10-03",
    "budget": "25000", "travelers": 2, "style_tags": ["relax"], "use_memory": True,
}


def queued_trip(client, monkeypatch, headers) -> str:
    """A trip left in 'processing' -- the job is not run, so the test can play
    the worker and publish events itself."""
    from app.routers import trips as trips_router

    monkeypatch.setattr(trips_router, "enqueue", lambda *a, **k: None)
    r = client.post("/trips", json=TRIP, headers=headers)
    assert r.json()["status"] == "processing"
    return r.json()["id"]


def close_code(ws) -> int:
    with pytest.raises(WebSocketDisconnect) as info:
        ws.receive_json()
    return info.value.code


# --- who may watch -------------------------------------------------------------

def test_no_auth_message_is_refused(client):
    me = signup(client)
    trip_id = create_trip(client, TRIP, me["headers"])["id"]
    with client.websocket_connect(f"/ws/trips/{trip_id}") as ws:
        ws.send_json({"type": "hello"})
        assert close_code(ws) == 4401


def test_a_bad_token_is_refused(client):
    me = signup(client)
    trip_id = create_trip(client, TRIP, me["headers"])["id"]
    with client.websocket_connect(f"/ws/trips/{trip_id}") as ws:
        ws.send_json({"type": "auth", "token": "not-a-jwt"})
        assert close_code(ws) == 4401


def test_another_users_trip_looks_like_no_trip(client):
    me = signup(client)
    trip_id = create_trip(client, TRIP, me["headers"])["id"]
    them = signup(client, OTHER)
    with client.websocket_connect(f"/ws/trips/{trip_id}") as ws:
        ws.send_json({"type": "auth", "token": them["token"]})
        assert close_code(ws) == 4404


# --- what they see ------------------------------------------------------------

def test_a_finished_trip_reports_done_straight_away(client):
    """Opening the page after generation finished must not hang on events that
    were published before anyone was listening."""
    me = signup(client)
    trip_id = create_trip(client, TRIP, me["headers"])["id"]
    with client.websocket_connect(f"/ws/trips/{trip_id}") as ws:
        ws.send_json({"type": "auth", "token": me["token"]})
        assert ws.receive_json() == {"type": "status", "status": "completed"}
        done = ws.receive_json()
        assert done["type"] == "done" and done["status"] == "completed"


def test_live_progress_is_relayed_in_order_then_done(client, monkeypatch):
    me = signup(client)
    trip_id = queued_trip(client, monkeypatch, me["headers"])

    with client.websocket_connect(f"/ws/trips/{trip_id}") as ws:
        ws.send_json({"type": "auth", "token": me["token"]})
        assert ws.receive_json() == {"type": "status", "status": "processing"}

        # Play the worker, from another thread -- as a real job would.
        progress.publish_progress(trip_id, "retrieving", "Looking through your past trips…")
        progress.publish_progress(trip_id, "generating", "Planning your days…")
        progress.publish_done(trip_id, "completed")

        steps = [ws.receive_json() for _ in range(3)]
    assert [e.get("step") for e in steps[:2]] == ["retrieving", "generating"]
    assert steps[2]["type"] == "done"
    assert [e["seq"] for e in steps] == sorted(e["seq"] for e in steps)


def test_a_late_watcher_gets_the_backlog_without_duplicates(client, monkeypatch):
    """Events published before the page connected arrive first, once each."""
    me = signup(client)
    trip_id = queued_trip(client, monkeypatch, me["headers"])

    progress.publish_progress(trip_id, "started", "Reading your request…")
    progress.publish_progress(trip_id, "retrieving", "Looking through your past trips…")

    with client.websocket_connect(f"/ws/trips/{trip_id}") as ws:
        ws.send_json({"type": "auth", "token": me["token"]})
        ws.receive_json()  # status
        first, second = ws.receive_json(), ws.receive_json()
        progress.publish_done(trip_id, "completed")
        done = ws.receive_json()

    assert [first["step"], second["step"]] == ["started", "retrieving"]
    assert done["type"] == "done"
    assert len({first["seq"], second["seq"], done["seq"]}) == 3


def test_the_real_job_publishes_every_step(client, monkeypatch):
    """End to end through the inline job: the broker's history holds the
    steps the browser would have seen."""
    me = signup(client)
    trip = create_trip(client, TRIP, me["headers"])
    history = list(progress.get_broker()._history[progress.channel_for(trip["id"])])
    steps = [e.get("step") for e in history if e["type"] == "progress"]
    assert steps == ["started", "retrieving", "thinking", "generating", "mapping", "saving"]
    thinking = next(e for e in history if e.get("step") == "thinking")
    assert thinking["thoughts"], "the thinking step carries the planner's reasoning"
    assert history[-1] == {**history[-1], "type": "done", "status": "completed"}


# --- the broker on its own ----------------------------------------------------

def test_local_broker_numbers_events_per_channel():
    b = progress.LocalBroker()
    a1 = b.publish("a", {"type": "progress"})
    a2 = b.publish("a", {"type": "progress"})
    other = b.publish("b", {"type": "progress"})
    assert (a1["seq"], a2["seq"], other["seq"]) == (1, 2, 1)


# --- the Redis broker (what Celery mode uses) ---------------------------------

def test_redis_broker_backlog_then_live_without_duplicates():
    """The production path: a worker process publishes, the API process
    subscribes. Run against fakeredis so it needs no Redis server."""
    import asyncio

    import fakeredis
    import fakeredis.aioredis

    server = fakeredis.FakeServer()
    broker = progress.RedisBroker(
        "redis://unused",
        client=fakeredis.FakeRedis(server=server),
        async_client_factory=lambda: fakeredis.aioredis.FakeRedis(server=server),
    )
    channel = progress.channel_for("trip-1")

    # Published before anyone listens -> must come back as backlog.
    broker.publish(channel, {"type": "progress", "step": "started"})

    async def watch():
        async with broker.subscribe(channel) as (backlog, queue):
            broker.publish(channel, {"type": "progress", "step": "generating"})
            broker.publish(channel, {"type": "done", "status": "completed"})
            live = [await asyncio.wait_for(queue.get(), 2) for _ in range(2)]
            return backlog, live

    backlog, live = asyncio.run(watch())
    assert [e["step"] for e in backlog] == ["started"]
    assert [e.get("step", e["type"]) for e in live] == ["generating", "done"]
    assert [e["seq"] for e in backlog + live] == [1, 2, 3]
