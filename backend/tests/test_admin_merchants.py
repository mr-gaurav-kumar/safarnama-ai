"""Admin managing merchants (business accounts): create, edit, block.

A blocked merchant must vanish for travellers everywhere: the package list,
a package's own page, the public business page and booking.
"""
from datetime import date, timedelta

from tests.helpers import OTHER, signup
from tests.test_business import PKG, _admin

NEW = {
    "owner_name": "Meera Iyer", "owner_email": "meera@coastaltrails.in", "password": "coastal-trails-7",
    "business_name": "Coastal Trails", "kind": "tour_operator", "city": "Kochi",
    "business_phone": "+91 98470 11223", "description": "Kerala backwaters.",
}
EDIT = {
    "business_name": "Coastal Trails Kerala", "kind": "tour_operator", "city": "Alleppey",
    "business_phone": "9847011223", "description": "Houseboats and backwaters.",
}


def _login(client, email, password):
    r = client.post("/auth/login", json={"email": email, "password": password})
    return r


def test_admin_creates_edits_and_blocks_a_merchant(client, session_factory):
    admin = _admin(client, session_factory)

    # --- create: live straight away, owner can log in and publish
    r = client.post("/admin/businesses", json=NEW, headers=admin)
    assert r.status_code == 201, r.text
    biz = r.json()
    assert biz["status"] == "approved" and biz["is_visible"] and not biz["owner_blocked"]
    assert biz["owner_email"] == "meera@coastaltrails.in" and biz["slug"] == "coastal-trails"
    assert client.post("/admin/businesses", json=NEW, headers=admin).status_code == 409

    login = _login(client, NEW["owner_email"], NEW["password"])
    assert login.status_code == 200 and login.json()["user"]["role"] == "business"
    owner = {"Authorization": f"Bearer {login.json()['access_token']}"}
    pkg = client.post("/business/packages", json=PKG, headers=owner).json()

    # --- edit: renaming moves the public page to the new handle
    r = client.put(f"/admin/businesses/{biz['user_id']}/profile", json=EDIT, headers=admin)
    assert r.status_code == 200, r.text
    assert r.json()["business_name"] == "Coastal Trails Kerala" and r.json()["city"] == "Alleppey"
    assert client.get("/businesses/coastal-trails-kerala").status_code == 200
    assert [p["id"] for p in client.get("/packages").json()] == [pkg["id"]]

    # --- block: hidden everywhere for travellers, and the owner is locked out
    traveller = signup(client, OTHER)["headers"]
    r = client.put(f"/admin/businesses/{biz['user_id']}/block", json={"blocked": True, "reason": "Fraud reports"}, headers=admin)
    assert r.status_code == 200 and r.json()["owner_blocked"] and not r.json()["is_visible"]
    assert r.json()["status"] == "approved"  # status is untouched; the block is separate

    assert client.get("/packages").json() == []
    assert client.get(f"/packages/{pkg['id']}").status_code == 404
    assert client.get("/businesses/coastal-trails-kerala").status_code == 404
    start = (date.today() + timedelta(days=10)).isoformat()
    booked = client.post(f"/packages/{pkg['id']}/book", json={"travelers": 1, "start_date": start}, headers=traveller)
    assert booked.status_code == 409
    assert _login(client, NEW["owner_email"], NEW["password"]).status_code == 403

    # The admin still sees it, under the "blocked" filter.
    blocked = client.get("/admin/businesses?status=blocked", headers=admin).json()
    assert blocked["total"] == 1 and blocked["items"][0]["status_reason"] == "Fraud reports"

    # --- unblock: everything comes back as it was
    r = client.put(f"/admin/businesses/{biz['user_id']}/block", json={"blocked": False}, headers=admin)
    assert r.json()["is_visible"]
    assert [p["id"] for p in client.get("/packages").json()] == [pkg["id"]]
    assert _login(client, NEW["owner_email"], NEW["password"]).status_code == 200


def test_blocking_the_owner_from_users_page_also_hides_packages(client, session_factory):
    """Blocking the login on the Users page must hide the merchant too -- not
    just the dedicated Block button."""
    admin = _admin(client, session_factory)
    biz = client.post("/admin/businesses", json=NEW, headers=admin).json()
    owner = {"Authorization": f"Bearer {_login(client, NEW['owner_email'], NEW['password']).json()['access_token']}"}
    client.post("/business/packages", json=PKG, headers=owner)
    assert len(client.get("/packages").json()) == 1

    client.put(f"/admin/users/{biz['user_id']}", json={"is_blocked": True}, headers=admin)
    assert client.get("/packages").json() == []
    assert client.get("/businesses/coastal-trails").status_code == 404


def test_only_admin_manages_merchants(client):
    user = signup(client)["headers"]
    assert client.post("/admin/businesses", json=NEW, headers=user).status_code == 403


def test_admin_created_merchant_can_start_pending(client, session_factory):
    admin = _admin(client, session_factory)
    biz = client.post("/admin/businesses", json={**NEW, "status": "pending"}, headers=admin).json()
    assert biz["status"] == "pending" and not biz["is_visible"]
