"""Agency / business accounts: sign-up, approval, publishing, bookings."""
from datetime import date, timedelta

from tests.helpers import OTHER, SIGNUP, signup

BIZ = {
    "name": "Ravi Sharma", "email": "ravi@sharmatravels.in", "password": "sharma-travels-9",
    "business_name": "Sharma  Travels", "kind": "agency", "city": "Jaipur",
    "business_phone": "+91 98290 12345", "description": "Rajasthan tours since 2009.",
    "gst_number": "08ABCDE1234F1Z5", "website": "sharmatravels.in",
}
PKG = {"title": "Royal Rajasthan", "destination": "Jaipur, Udaipur", "duration_days": 6, "price_per_person": 24999}


def _admin(client, session_factory):
    from app.models.user import User
    me = signup(client)
    with session_factory() as db:
        u = db.query(User).filter_by(email=SIGNUP["email"]).one()
        u.role = "admin"
        u.is_verified = True  # the real admin is always verified
        db.commit()
    return me["headers"]


def test_business_signup_needs_approval_before_publishing(client, session_factory):
    admin = _admin(client, session_factory)
    r = client.post("/auth/signup-business", json=BIZ)
    assert r.status_code == 201, r.text
    assert r.json()["user"]["role"] == "business"
    biz = {"Authorization": f"Bearer {r.json()['access_token']}"}

    me = client.get("/business/me", headers=biz).json()
    assert me["status"] == "pending" and me["slug"] == "sharma-travels"
    assert me["business_name"] == "Sharma Travels" and me["website"] == "https://sharmatravels.in"
    assert client.post("/business/packages", json=PKG, headers=biz).status_code == 403

    listed = client.get("/admin/businesses?status=pending", headers=admin).json()
    assert listed["total"] == 1
    assert client.get("/admin/stats", headers=admin).json()["businesses_pending"] == 1
    r = client.put(f"/admin/businesses/{me['user_id']}", json={"status": "approved"}, headers=admin)
    assert r.json()["status"] == "approved"

    pkg = client.post("/business/packages", json=PKG, headers=biz)
    assert pkg.status_code == 201, pkg.text
    pkg = pkg.json()
    public = client.get("/packages").json()
    assert public[0]["business_name"] == "Sharma Travels" and public[0]["business_slug"] == "sharma-travels"
    page = client.get("/businesses/sharma-travels").json()
    assert page["business"]["city"] == "Jaipur" and len(page["packages"]) == 1

    # A traveller books; only the owning business sees it.
    user = signup(client, OTHER)["headers"]
    start = (date.today() + timedelta(days=15)).isoformat()
    b = client.post(f"/packages/{pkg['id']}/book", json={"travelers": 2, "start_date": start}, headers=user).json()
    mine = client.get("/business/bookings", headers=biz).json()
    assert mine["total"] == 1 and mine["items"][0]["user_email"] == OTHER["email"]
    assert client.put(f"/business/bookings/{b['id']}", json={"status": "confirmed"}, headers=biz).json()["status"] == "confirmed"

    # Suspending hides everything the business published.
    client.put(f"/admin/businesses/{me['user_id']}", json={"status": "suspended", "reason": "Complaints"}, headers=admin)
    assert client.get("/packages").json() == []
    assert client.get("/businesses/sharma-travels").status_code == 404


def test_travellers_cannot_use_business_routes(client):
    user = signup(client)["headers"]
    assert client.get("/business/me", headers=user).status_code == 403


def test_bad_gst_is_rejected(client):
    r = client.post("/auth/signup-business", json={**BIZ, "gst_number": "12345"})
    assert r.status_code == 422


# --- AI fill for blank package fields -------------------------------------------

def _biz(client):
    r = client.post("/auth/signup-business", json=BIZ)
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_fill_suggests_only_blank_fields_without_ai(client):
    biz = _biz(client)  # a pending business can already draft
    body = {"destination": "Manali", "duration_days": 4, "price_per_person": 18000,
            "title": "Snow Week by Sharma", "inclusions": ["Volvo bus from Delhi"]}
    r = client.post("/business/packages/fill", json=body, headers=biz)
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["source"] == "rules"
    assert "title" not in out["fields"] and "inclusions" not in out["fields"]  # theirs, untouched
    f = out["fields"]
    assert len(f["highlights"]) == 4 and f["highlights"][0].startswith("Day 1: Arrive in Manali")
    assert f["summary"] and f["description"] and "adventure" in f["style_tags"]


def test_fill_with_ai_and_checks(client, monkeypatch):
    import json as _json
    from app.core.config import settings
    from app.llm import package_fill
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test")
    good = {"title": "Kerala Backwaters & Hills", "summary": "s", "description": "d",
            "inclusions": ["AC car with driver", "Daily breakfast", "Houseboat night"],
            "highlights": ["Day 1: Kochi", "Day 2: Munnar", "Day 3: Alleppey"], "style_tags": ["relax", "made-up"]}
    answers = [_json.dumps({**good, "highlights": ["Day 1: Kochi"]}), _json.dumps(good)]  # first fails the day count
    monkeypatch.setattr(package_fill, "_call", lambda prompt: answers.pop(0))
    out = client.post("/business/packages/fill", json={"destination": "Kochi, Munnar", "duration_days": 3,
                                                       "price_per_person": 21000}, headers=_biz(client)).json()
    assert out["source"] == "ai" and out["fields"]["inclusions"][0] == "AC car with driver"
    assert out["fields"]["style_tags"] == ["relax"]  # unknown tags dropped


def test_fill_needs_a_business_or_admin(client):
    me = signup(client, OTHER)
    body = {"destination": "Goa", "duration_days": 3, "price_per_person": 9000}
    assert client.post("/business/packages/fill", json=body, headers=me["headers"]).status_code == 403
    assert client.post("/admin/packages/fill", json=body, headers=me["headers"]).status_code == 403
