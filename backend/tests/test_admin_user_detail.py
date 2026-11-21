"""Admin: one user's full record, profile edits, trip status changes."""
from tests.helpers import OTHER, SIGNUP, signup


def _make_admin(client, session_factory):
    from app.models.user import User
    me = signup(client)
    with session_factory() as db:
        u = db.query(User).filter_by(email=SIGNUP["email"]).one()
        u.role = "admin"
        u.is_verified = True  # the real admin is always verified
        db.commit()
    return me["headers"]


def test_admin_sees_full_user_record_and_can_edit_it(client, session_factory):
    headers = _make_admin(client, session_factory)
    other = client.post("/auth/signup", json={**OTHER, "home_town": "Pune", "date_of_birth": "1999-01-02"}).json()
    uid = other["user"]["id"]

    r = client.get(f"/admin/users/{uid}", headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["home_town"] == "Pune" and body["date_of_birth"] == "1999-01-02"
    assert body["trips"] == [] and body["login_count"] == 0

    r = client.put(f"/admin/users/{uid}", json={"home_town": "Mumbai", "is_blocked": True}, headers=headers)
    assert r.status_code == 200
    assert r.json()["home_town"] == "Mumbai" and r.json()["is_blocked"] is True


def test_non_admin_cannot_read_user_records(client):
    headers = signup(client)["headers"]
    other = client.post("/auth/signup", json=OTHER).json()
    assert client.get(f"/admin/users/{other['user']['id']}", headers=headers).status_code == 403
