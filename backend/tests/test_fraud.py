"""Risk scoring (§4.12): the five named rules, de-duplication, the Isolation
Forest, and the promise that a flag never blocks anyone by itself."""
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.security import hash_password
from app.fraud import events, scorer
from app.models.risk import ActivityEvent, FraudFlag
from app.models.user import User
from tests.helpers import SIGNUP, signup


def _user(db, email=None) -> User:
    u = User(name="T", email=email or f"{uuid.uuid4().hex[:8]}@example.com",
             password_hash=hash_password("x-password-123"))
    db.add(u)
    db.commit()
    return u


def _events(db, user, kind, n, ip="10.0.0.1", ago=timedelta(0)):
    for i in range(n):
        db.add(ActivityEvent(kind=kind, user_id=user.id if user else None,
                             ip=ip(i) if callable(ip) else ip,
                             created_at=datetime.now(timezone.utc) - ago))
    db.commit()


def _reasons(flags):
    return sorted(f.reason for f in flags)


# --- rules ------------------------------------------------------------------------

def test_trip_burst_flags_at_the_threshold_and_records_what_it_counted(db_session):
    u = _user(db_session)
    _events(db_session, u, "trip_created", 5)
    flags = scorer.score_user(db_session, u.id)
    assert _reasons(flags) == ["trip_burst"]
    f = flags[0]
    assert f.risk_score == 0.8 and f.status == "open"
    assert f.details == {"count": 5, "threshold": 5, "window_minutes": 10}


def test_one_below_the_threshold_is_not_flagged(db_session):
    u = _user(db_session)
    _events(db_session, u, "trip_created", 4)
    _events(db_session, u, "invite_sent", 9)
    _events(db_session, u, "login_failed", 4)
    assert scorer.score_user(db_session, u.id) == []


def test_events_outside_the_window_do_not_count(db_session):
    u = _user(db_session)
    _events(db_session, u, "trip_created", 10, ago=timedelta(minutes=30))
    assert scorer.score_user(db_session, u.id) == []


def test_invite_burst_and_login_failures(db_session):
    u = _user(db_session)
    _events(db_session, u, "invite_sent", 10)
    _events(db_session, u, "login_failed", 5)
    assert _reasons(scorer.score_user(db_session, u.id)) == ["invite_burst", "login_failures"]


def test_many_accounts_from_one_ip(db_session):
    users = [_user(db_session) for _ in range(3)]
    for u in users:
        _events(db_session, u, "signup", 1, ip="203.0.113.7")
    flags = scorer.score_user(db_session, users[-1].id, "203.0.113.7")
    assert _reasons(flags) == ["many_accounts_one_ip"]
    assert flags[0].details["ip"] == "203.0.113.7"
    # A different IP with one account is fine.
    lone = _user(db_session)
    _events(db_session, lone, "signup", 1, ip="198.51.100.1")
    assert scorer.score_user(db_session, lone.id, "198.51.100.1") == []


def test_ip_hopping(db_session):
    u = _user(db_session)
    _events(db_session, u, "login_ok", 4, ip=lambda i: f"10.0.0.{i + 1}")
    assert _reasons(scorer.score_user(db_session, u.id)) == ["ip_hopping"]


def test_same_reason_is_flagged_once_while_open(db_session):
    u = _user(db_session)
    _events(db_session, u, "trip_created", 6)
    assert len(scorer.score_user(db_session, u.id)) == 1
    _events(db_session, u, "trip_created", 3)
    assert scorer.score_user(db_session, u.id) == []
    assert db_session.scalar(select(FraudFlag).where(FraudFlag.user_id == u.id)) is not None
    # Once an admin closes it, a fresh burst raises a fresh flag.
    for f in db_session.scalars(select(FraudFlag)):
        f.status = "resolved"
    db_session.commit()
    assert len(scorer.score_user(db_session, u.id)) == 1


def test_a_flag_never_blocks_the_user(db_session):
    u = _user(db_session)
    _events(db_session, u, "trip_created", 20)
    _events(db_session, u, "login_failed", 20)
    assert scorer.score_user(db_session, u.id)
    db_session.refresh(u)
    assert u.is_blocked is False


# --- the model -----------------------------------------------------------------------

def test_forest_waits_for_enough_users(db_session):
    users = [_user(db_session) for _ in range(scorer.MIN_POPULATION - 1)]
    for u in users:
        _events(db_session, u, "login_ok", 1)
    assert scorer.forest_score(db_session, users[0].id) is None


def test_forest_flags_an_unusual_mix_that_no_rule_catches(db_session):
    normal = [_user(db_session) for _ in range(30)]
    for i, u in enumerate(normal):
        _events(db_session, u, "login_ok", 1)
        _events(db_session, u, "trip_created", 1 + i % 2)
    odd = _user(db_session)
    # Every count just under its rule's threshold -- together, very unusual.
    _events(db_session, odd, "trip_created", 4)
    _events(db_session, odd, "invite_sent", 9)
    _events(db_session, odd, "login_failed", 4)
    _events(db_session, odd, "login_ok", 3, ip=lambda i: f"10.9.0.{i + 1}")
    _events(db_session, odd, "match_request", 6)

    flags = scorer.score_user(db_session, odd.id)
    assert _reasons(flags) == ["anomalous_activity"]
    assert 0.5 <= flags[0].risk_score <= 1.0
    assert flags[0].details["population"] == 31
    assert flags[0].details["features"]["invites_24h"] == 9
    # An ordinary user in the same population is left alone.
    assert scorer.forest_score(db_session, normal[0].id) is None


# --- wired into the API -----------------------------------------------------------------

def test_failed_logins_through_the_api_raise_a_flag(client, db_session):
    signup(client)
    for _ in range(5):
        r = client.post("/auth/login", json={"email": SIGNUP["email"], "password": "wrong-password"})
        assert r.status_code == 401
        assert r.json() == {"detail": "Incorrect email or password"}
    flags = db_session.scalars(select(FraudFlag)).all()
    assert [f.reason for f in flags] == ["login_failures"]


def test_unknown_email_failures_are_recorded_without_a_user(client, db_session):
    r = client.post("/auth/login", json={"email": "nobody@example.com", "password": "whatever-123"})
    assert r.status_code == 401
    ev = db_session.scalars(select(ActivityEvent).where(ActivityEvent.kind == "login_failed")).all()
    assert len(ev) == 1 and ev[0].user_id is None


def test_record_rejects_unknown_kinds(db_session):
    import pytest

    with pytest.raises(AssertionError):
        events.record(db_session, "made_up", user_id=None, ip=None)
