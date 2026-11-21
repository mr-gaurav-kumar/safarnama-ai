"""Rate limits on every endpoint (§4.13): which bucket a request lands in, who
it counts against, and what a client sees when it is over."""
from types import SimpleNamespace

import pytest

from app.core import ratelimit
from app.core.config import settings
from tests.helpers import OTHER, SIGNUP, auth
from tests.test_trip_routes import TRIP


@pytest.fixture
def limits(monkeypatch):
    """Rate limiting on, with small limits so tests stay quick."""
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)
    # Pin the clock mid-window so a minute boundary can't reset a count mid-test.
    monkeypatch.setattr(ratelimit, "time", SimpleNamespace(time=lambda: 1_000_030.0))

    def set_(**kw):
        for name, value in kw.items():
            monkeypatch.setattr(settings, f"RATE_LIMIT_{name.upper()}_PER_MIN", value)
    return set_


def _login_wrong(client):
    return client.post("/auth/login", json={"email": SIGNUP["email"], "password": "nope-nope-1"})


def test_login_is_limited_per_ip_with_retry_after(client, limits):
    limits(auth=3)
    assert [_login_wrong(client).status_code for _ in range(3)] == [401, 401, 401]
    r = _login_wrong(client)
    assert r.status_code == 429
    retry = int(r.headers["retry-after"])
    assert retry == 50  # seconds left in the pinned window
    assert r.json()["retry_after"] == retry
    assert "Too many requests" in r.json()["detail"]


def test_signup_and_login_share_the_auth_bucket(client, limits):
    limits(auth=2)
    assert client.post("/auth/signup", json=SIGNUP).status_code in (200, 201)
    assert _login_wrong(client).status_code == 401
    assert client.post("/auth/signup", json=OTHER).status_code == 429


def test_reads_are_counted_per_user_not_per_ip(client, limits):
    limits(auth=50, reads=3)
    garv, riya = auth(client), auth(client, OTHER)
    assert [client.get("/trips", headers=garv).status_code for _ in range(3)] == [200] * 3
    assert client.get("/trips", headers=garv).status_code == 429
    # Same IP, different user: their own allowance.
    assert client.get("/trips", headers=riya).status_code == 200


def test_new_trips_have_their_own_tighter_bucket(client, limits):
    limits(auth=50, trips=2)
    h = auth(client)
    assert [client.post("/trips", json=TRIP, headers=h).status_code for _ in range(2)] == [202, 202]
    assert client.post("/trips", json=TRIP, headers=h).status_code == 429
    # Reading is unaffected.
    assert client.get("/trips", headers=h).status_code == 200


def test_writes_bucket(client, limits):
    limits(auth=50, writes=1, trips=50)
    h = auth(client)
    trip = client.post("/trips", json=TRIP, headers=h).json()
    assert client.delete(f"/trips/{trip['id']}", headers=h).status_code == 204
    assert client.delete(f"/trips/{trip['id']}", headers=h).status_code == 429


def test_anonymous_reads_fall_back_to_the_ip(client, limits):
    limits(reads=2)
    codes = [client.get("/trips").status_code for _ in range(3)]
    assert codes[:2] == [401, 401] and codes[2] == 429


def test_health_is_never_limited(client, limits):
    limits(reads=1)
    assert {client.get("/health").status_code for _ in range(5)} == {200}


def test_switched_off_means_no_limits(client, limits, monkeypatch):
    limits(auth=1)
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", False)
    assert {_login_wrong(client).status_code for _ in range(5)} == {401}
