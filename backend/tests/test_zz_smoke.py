"""End-to-end smoke test with the real rate limits ON -- one normal user
session (sign up, verify, plan, a few rounds of page loads, reloads) and every
admin read. Guards against a limit set so tight that ordinary use trips it."""
from app.core.config import settings
from app.models.user import User
from tests.helpers import create_trip, verified

TRIP = {"destination": "Goa", "start_date": "2026-12-20", "end_date": "2026-12-23",
        "budget": "30000", "travelers": 2, "style_tags": ["relax"], "use_memory": True}

PAGE_LOADS = ("/auth/me", "/trips", "/trips/{id}", "/trips/{id}/members",
              "/trips/{id}/feedback", "/invitations", "/insights", "/chat/history")

ADMIN_READS = ("/admin/stats", "/admin/users", "/admin/trips", "/admin/fraud-flags",
               "/admin/escalations", "/admin/feedback", "/admin/chat-logs", "/admin/audit")


def test_normal_use_never_hits_the_default_limits(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)
    me = verified(client)
    h = me["headers"]
    trip = create_trip(client, TRIP, h)

    codes = {client.get(p.format(id=trip["id"]), headers=h).status_code
             for _ in range(8) for p in PAGE_LOADS}
    assert codes == {200}

    for _ in range(5):  # page reloads
        assert client.post("/auth/refresh", headers={"X-Requested-With": "fetch"}).status_code == 200


def test_every_admin_page_loads(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)
    me = verified(client)
    create_trip(client, TRIP, me["headers"])
    u = db_session.query(User).one()
    u.role = "admin"
    db_session.commit()

    for path in ADMIN_READS:
        r = client.get(path, headers=me["headers"])
        assert r.status_code == 200, (path, r.status_code, r.text[:200])
    s = client.get("/admin/stats", headers=me["headers"]).json()
    assert s["users_total"] == 1 and s["trips_total"] == 1
