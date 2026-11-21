"""Admin API (§4.14): who gets in, the self-lockout guards, blocking, the
fraud-flag review flow, fixing a stuck trip, and the audit trail.

The admin here is the verified ADMIN_EMAIL account (garv@example.com in tests).
"""
from sqlalchemy import select

from app.models.refresh_token import RefreshToken
from app.models.risk import AdminAction, FraudFlag
from app.models.trip import Trip
from app.models.user import User
from tests.helpers import OTHER, SIGNUP, create_trip, verified
from tests.test_trip_routes import TRIP

READS = ("/admin/stats", "/admin/users", "/admin/trips", "/admin/fraud-flags",
         "/admin/escalations", "/admin/feedback", "/admin/chat-logs", "/admin/audit")


def _setup(client, db):
    admin = verified(client)  # garv@example.com -> admin on verifying
    riya = verified(client, OTHER)
    riya_id = db.scalar(select(User.id).where(User.email == OTHER["email"]))
    return admin["headers"], riya["headers"], riya_id


def _actions(db):
    db.expire_all()
    return [a.action for a in db.scalars(select(AdminAction).order_by(AdminAction.created_at))]


def test_only_the_admin_gets_in(client, db_session):
    admin, riya, _ = _setup(client, db_session)
    for path in READS:
        assert client.get(path).status_code == 401, path
        assert client.get(path, headers=riya).status_code == 403, path
        assert client.get(path, headers=admin).status_code == 200, path


def test_admin_cannot_block_or_delete_themselves(client, db_session):
    admin, _, _ = _setup(client, db_session)
    me = db_session.scalar(select(User).where(User.email == SIGNUP["email"]))
    assert client.put(f"/admin/users/{me.id}", json={"is_blocked": True}, headers=admin).status_code == 409
    assert client.delete(f"/admin/users/{me.id}", headers=admin).status_code == 409
    db_session.refresh(me)
    assert me.is_blocked is False and me.role == "admin"


def test_blocking_signs_the_user_out_everywhere(client, db_session):
    admin, riya, riya_id = _setup(client, db_session)
    r = client.put(f"/admin/users/{riya_id}", json={"is_blocked": True}, headers=admin)
    assert r.status_code == 200 and r.json()["is_blocked"] is True

    db_session.expire_all()
    tokens = db_session.scalars(select(RefreshToken).where(RefreshToken.user_id == riya_id)).all()
    assert tokens and all(t.revoked_at is not None for t in tokens)
    assert client.get("/trips", headers=riya).status_code in (401, 403)
    login = client.post("/auth/login", json={"email": OTHER["email"], "password": OTHER["password"]})
    assert login.status_code == 403
    assert "user.update" in _actions(db_session)


def test_review_a_fraud_flag_and_block_from_the_same_screen(client, db_session):
    admin, _, riya_id = _setup(client, db_session)
    low = FraudFlag(user_id=riya_id, reason="ip_hopping", risk_score=0.6, details={}, status="open")
    high = FraudFlag(user_id=riya_id, reason="trip_burst", risk_score=0.8, details={"count": 7}, status="open")
    db_session.add_all([low, high])
    db_session.commit()

    page = client.get("/admin/fraud-flags", headers=admin).json()
    assert page["total"] == 2
    assert [f["reason"] for f in page["items"]] == ["trip_burst", "ip_hopping"], "riskiest first"
    assert client.get("/admin/stats", headers=admin).json()["open_fraud_flags"] == 2

    r = client.put(f"/admin/fraud-flags/{high.id}", json={"status": "resolved", "block_user": True},
                   headers=admin)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "resolved" and body["user_blocked"] is True and body["reviewed_at"]

    r = client.put(f"/admin/fraud-flags/{low.id}", json={"status": "dismissed"}, headers=admin)
    assert r.json()["status"] == "dismissed"
    assert client.get("/admin/fraud-flags", headers=admin).json()["total"] == 0, "only open ones by default"
    assert client.get("/admin/fraud-flags?status=resolved", headers=admin).json()["total"] == 1
    assert _actions(db_session).count("flag.review") == 2


def test_cannot_block_yourself_through_a_flag(client, db_session):
    admin, _, _ = _setup(client, db_session)
    me = db_session.scalar(select(User).where(User.email == SIGNUP["email"]))
    f = FraudFlag(user_id=me.id, reason="ip_hopping", risk_score=0.6, details={}, status="open")
    db_session.add(f)
    db_session.commit()
    r = client.put(f"/admin/fraud-flags/{f.id}", json={"status": "resolved", "block_user": True}, headers=admin)
    assert r.status_code == 409


def test_a_stuck_trip_can_be_marked_failed_so_the_owner_can_retry(client, db_session):
    admin, riya, _ = _setup(client, db_session)
    trip = create_trip(client, TRIP, riya)
    row = db_session.get(Trip, __import__("uuid").UUID(trip["id"]))
    row.status = "processing"  # e.g. the worker died mid-generation
    db_session.commit()
    assert client.get("/admin/stats", headers=admin).json()["trips_processing"] == 1

    r = client.put(f"/admin/trips/{trip['id']}", json={"status": "failed"}, headers=admin)
    assert r.status_code == 200 and r.json()["status"] == "failed"
    mine = client.get(f"/trips/{trip['id']}", headers=riya).json()
    assert mine["status"] == "failed" and "plan this trip again" in mine["error"]
    assert "trip.update" in _actions(db_session)


def test_audit_log_names_the_admin(client, db_session):
    admin, _, riya_id = _setup(client, db_session)
    client.put(f"/admin/users/{riya_id}", json={"is_blocked": True}, headers=admin)
    lines = client.get("/admin/audit", headers=admin).json()["items"]
    assert lines[0]["admin_email"] == SIGNUP["email"]
    assert lines[0]["action"] == "user.update" and lines[0]["target_id"] == str(riya_id)


def test_role_cannot_be_granted_through_the_api(client, db_session):
    admin, riya, riya_id = _setup(client, db_session)
    r = client.put(f"/admin/users/{riya_id}", json={"role": "admin"}, headers=admin)
    assert r.status_code == 200 and r.json()["role"] == "user"
    assert client.get("/admin/stats", headers=riya).status_code == 403
