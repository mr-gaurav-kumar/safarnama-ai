"""Admin-published travel packages, traveller bookings, and the one-admin rule."""
from datetime import date, timedelta

from tests.helpers import OTHER, SIGNUP, signup

PKG = {
    "title": "Golden Triangle Classic", "destination": "Delhi, Agra, Jaipur", "duration_days": 5,
    "price_per_person": 18999, "summary": "Forts, palaces and the Taj.",
    "inclusions": ["Hotels", "Breakfast", "Hotels"], "highlights": ["Taj Mahal at sunrise"],
    "style_tags": ["culture"], "seats": 4,
}


def _admin(client, session_factory):
    from app.models.user import User
    me = signup(client)
    with session_factory() as db:
        u = db.query(User).filter_by(email=SIGNUP["email"]).one()
        u.role = "admin"
        u.is_verified = True  # the real admin is always verified
        db.commit()
    return me["headers"]


def test_admin_publishes_and_traveller_books(client, session_factory):
    admin = _admin(client, session_factory)
    r = client.post("/admin/packages", json=PKG, headers=admin)
    assert r.status_code == 201, r.text
    pkg = r.json()
    assert pkg["inclusions"] == ["Hotels", "Breakfast"] and pkg["seats_left"] == 4

    listed = client.get("/packages").json()          # public
    assert [p["title"] for p in listed] == ["Golden Triangle Classic"]

    user = signup(client, OTHER)["headers"]
    start = (date.today() + timedelta(days=20)).isoformat()
    b = client.post(f"/packages/{pkg['id']}/book", json={"travelers": 3, "start_date": start}, headers=user)
    assert b.status_code == 201, b.text
    assert b.json()["total_price"] == 3 * 18999 and b.json()["status"] == "pending"

    too_many = client.post(f"/packages/{pkg['id']}/book", json={"travelers": 2, "start_date": start}, headers=user)
    assert too_many.status_code == 409  # only 1 seat left

    mine = client.get("/packages/bookings/mine", headers=user).json()
    assert len(mine) == 1

    bookings = client.get("/admin/package-bookings", headers=admin).json()
    assert bookings["total"] == 1 and bookings["items"][0]["user_email"] == OTHER["email"]
    r = client.put(f"/admin/package-bookings/{bookings['items'][0]['id']}", json={"status": "confirmed"}, headers=admin)
    assert r.json()["status"] == "confirmed"

    # Hidden packages disappear for travellers.
    client.put(f"/admin/packages/{pkg['id']}", json={**PKG, "is_active": False}, headers=admin)
    assert client.get("/packages").json() == []


def test_travellers_cannot_manage_packages(client):
    user = signup(client)["headers"]
    assert client.post("/admin/packages", json=PKG, headers=user).status_code == 403


def test_admin_panel_cannot_promote_anyone(client, session_factory):
    admin = _admin(client, session_factory)
    other = client.post("/auth/signup", json=OTHER).json()["user"]
    r = client.put(f"/admin/users/{other['id']}", json={"role": "admin"}, headers=admin)
    assert r.status_code == 200 and r.json()["role"] == "user"
    created = client.post("/admin/users", json={
        "name": "Aman", "email": "aman@example.com", "password": "third-password3", "role": "admin",
    }, headers=admin)
    assert created.status_code == 201 and created.json()["role"] == "user"


def test_admin_edits_and_creates_trips_for_a_user(client, session_factory):
    admin = _admin(client, session_factory)
    other = client.post("/auth/signup", json=OTHER).json()["user"]
    start = date.today() + timedelta(days=10)
    r = client.post(f"/admin/users/{other['id']}/trips", json={
        "destination": "Goa", "start_date": start.isoformat(), "end_date": (start + timedelta(days=2)).isoformat(),
        "budget": "20000", "travelers": 2, "style_tags": ["relax"], "use_memory": False,
    }, headers=admin)
    assert r.status_code == 202, r.text
    trip_id = r.json()["id"]
    r = client.put(f"/admin/trips/{trip_id}", json={"destination": "North Goa", "budget": 25000, "travelers": 3}, headers=admin)
    assert r.status_code == 200 and r.json()["destination"] == "North Goa" and r.json()["travelers"] == 3
    bad = client.put(f"/admin/trips/{trip_id}", json={"end_date": (start - timedelta(days=1)).isoformat()}, headers=admin)
    assert bad.status_code == 422
