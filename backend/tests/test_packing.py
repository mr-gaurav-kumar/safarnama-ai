"""Packing lists: weather-aware suggestions, the traveller's own list with
going / return ticks, and the admin's default items that only the admin
can remove."""
from app.services import packing_service
from tests.helpers import OTHER, create_trip, signup, verified
from tests.test_business import _admin

MANALI_DEC = {"destination": "Manali", "start_date": "2026-12-20", "end_date": "2026-12-24",
              "budget": "40000", "travelers": 2, "style_tags": ["adventure", "nature"], "use_memory": False}
GOA_MAY = {"destination": "Goa", "start_date": "2027-05-10", "end_date": "2027-05-13",
           "budget": "40000", "travelers": 2, "style_tags": ["relax"], "use_memory": False}


def _names(suggestions: dict) -> set[str]:
    return {s["name"] for s in suggestions["items"]}


def test_hill_trip_in_winter_suggests_warm_clothes_and_boots(client):
    h = signup(client)["headers"]
    trip = create_trip(client, MANALI_DEC, h)
    s = client.get(f"/trips/{trip['id']}/packing/suggestions", headers=h).json()
    names = _names(s)
    assert s["source"] == "rules"
    assert {"Heavy jacket", "Thermal inner set", "Gloves (pair)", "Waterproof boots", "Full-sleeve T-shirts"} <= names
    assert "Swimwear" not in names and "Half-sleeve cotton T-shirts" not in names
    assert any("cold" in line for line in s["context"])
    # Quantities follow the number of days (5 days -> 5 tops, 6 underwear).
    by_name = {x["name"]: x["quantity"] for x in s["items"]}
    assert by_name["Full-sleeve T-shirts"] == 5 and by_name["Underwear"] == 6


def test_beach_trip_in_summer_suggests_light_clothes(client):
    h = signup(client)["headers"]
    trip = create_trip(client, GOA_MAY, h)
    names = _names(client.get(f"/trips/{trip['id']}/packing/suggestions", headers=h).json())
    assert {"Half-sleeve cotton T-shirts", "Shorts", "Sunscreen", "Swimwear", "Sandals / floaters"} <= names
    assert "Heavy jacket" not in names and "Thermal inner set" not in names


def test_list_add_tick_going_and_return_and_delete(client):
    h = signup(client)["headers"]
    trip = create_trip(client, MANALI_DEC, h)
    base = f"/trips/{trip['id']}/packing"

    assert client.get(base, headers=h).json()["items"] == []
    s = client.get(f"{base}/suggestions", headers=h).json()["items"][:3]
    lst = client.post(f"{base}/bulk", json={"items": [{k: x[k] for k in ("name", "category", "quantity")} for x in s]}, headers=h).json()
    assert lst["progress"]["total"] == 3 and all(i["source"] == "ai" for i in lst["items"])

    lst = client.post(base, json={"name": "Vest", "category": "clothes", "quantity": 4}, headers=h).json()
    vest = next(i for i in lst["items"] if i["name"] == "Vest")
    assert vest["quantity"] == 4 and vest["source"] == "mine"
    # Same name again is refused, any case.
    assert client.post(base, json={"name": "vest", "category": "clothes"}, headers=h).status_code == 409

    lst = client.patch(f"{base}/{vest['id']}", json={"packed_going": True, "quantity": 5}, headers=h).json()
    assert lst["progress"]["packed_going"] == 1 and lst["progress"]["packed_return"] == 0
    lst = client.patch(f"{base}/{vest['id']}", json={"packed_return": True}, headers=h).json()
    assert lst["progress"]["packed_return"] == 1
    lst = client.post(f"{base}/reset/return", headers=h).json()
    assert lst["progress"]["packed_return"] == 0 and lst["progress"]["packed_going"] == 1

    lst = client.delete(f"{base}/{vest['id']}", headers=h).json()
    assert lst["progress"]["total"] == 3
    # Suggestions skip what is already on the list.
    again = _names(client.get(f"{base}/suggestions", headers=h).json())
    assert not ({x["name"] for x in s} & again)


def test_lists_are_private(client):
    garv = signup(client)["headers"]
    trip = create_trip(client, GOA_MAY, garv)
    item = client.post(f"/trips/{trip['id']}/packing", json={"name": "Hat"}, headers=garv).json()["items"][0]
    riya = signup(client, OTHER)["headers"]
    assert client.get(f"/trips/{trip['id']}/packing", headers=riya).status_code == 404
    assert client.patch(f"/trips/{trip['id']}/packing/{item['id']}", json={"packed_going": True}, headers=riya).status_code == 404


def test_admin_defaults_everyone_and_one_person_locked_for_traveller(client, session_factory):
    admin = _admin(client, session_factory)
    riya = verified(client, OTHER)["headers"]
    trip = create_trip(client, GOA_MAY, riya)
    base = f"/trips/{trip['id']}/packing"

    everyone = client.post("/admin/packing-defaults", json={"name": "Government photo ID", "category": "documents",
                                                             "note": "Required at hotels"}, headers=admin)
    assert everyone.status_code == 201 and everyone.json()["user_email"] is None
    only_riya = client.post("/admin/packing-defaults", json={"name": "Inhaler", "category": "health",
                                                             "user_email": OTHER["email"]}, headers=admin).json()
    assert only_riya["user_email"] == OTHER["email"]
    assert client.post("/admin/packing-defaults", json={"name": "X", "user_email": "nobody@example.com"},
                       headers=admin).status_code == 404

    items = {i["name"]: i for i in client.get(base, headers=riya).json()["items"]}
    assert items["Government photo ID"]["locked"] and items["Government photo ID"]["source"] == "admin"
    assert items["Government photo ID"]["note"] == "Required at hotels"
    assert "Inhaler" in items

    # The traveller can tick it, but not change or remove it.
    gid = items["Government photo ID"]["id"]
    assert client.patch(f"{base}/{gid}", json={"packed_going": True}, headers=riya).status_code == 200
    assert client.patch(f"{base}/{gid}", json={"quantity": 3}, headers=riya).status_code == 403
    assert client.delete(f"{base}/{gid}", headers=riya).status_code == 403

    # Admin edits flow through; admin delete removes it from every list.
    client.put(f"/admin/packing-defaults/{only_riya['id']}", json={"name": "Inhaler (spare)", "category": "health",
                                                                  "quantity": 2}, headers=admin)
    names = {i["name"] for i in client.get(base, headers=riya).json()["items"]}
    assert "Inhaler (spare)" in names and "Inhaler" not in names
    assert client.delete(f"/admin/packing-defaults/{everyone.json()['id']}", headers=admin).status_code == 204
    names = {i["name"] for i in client.get(base, headers=riya).json()["items"]}
    assert "Government photo ID" not in names

    # Someone else does not get Riya's personal item.
    other = signup(client, {"name": "Aman", "email": "aman2@example.com", "password": "third-password3"})["headers"]
    t2 = create_trip(client, GOA_MAY, other)
    assert all(i["name"] != "Inhaler (spare)" for i in client.get(f"/trips/{t2['id']}/packing", headers=other).json()["items"])


def test_only_admin_manages_defaults(client):
    h = signup(client)["headers"]
    assert client.get("/admin/packing-defaults", headers=h).status_code == 403


def test_rules_never_name_a_medicine():
    f = packing_service.TripFacts("Leh", 6, ["cold"], False, 3500, ["adventure"], ["Jan"])
    names = {s.name for s in packing_service.rule_suggestions(f)}
    assert "Your regular medicines" in names and "Waterproof boots" in names
