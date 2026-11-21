"""Plans the traveller writes, edits and plans again -- no AI involved."""
from tests.helpers import OTHER, auth, create_trip

OWN = {
    "destination": "Rishikesh", "start_date": "2026-12-10", "end_date": "2026-12-12",
    "travelers": 2, "style_tags": ["adventure"], "notes": "College friends trip",
    "days": [
        {"items": [{"time": "14:00", "activity": "River rafting", "place": "Shivpuri", "estimated_cost": 1500},
                   {"time": "09:00", "activity": "Reach by bus", "place": "ISBT"}]},
        {"items": [{"activity": "Cafe hopping", "place": "Tapovan"}]},
    ],
}


def test_own_plan_is_saved_ready_at_once(client):
    h = auth(client)
    r = client.post("/trips/own", json=OWN, headers=h)
    assert r.status_code == 201, r.text
    trip = r.json()
    assert trip["status"] == "completed" and trip["source"] == "manual"
    days = trip["itinerary"]["day_plan"]
    assert [d["date"] for d in days] == ["2026-12-10", "2026-12-11", "2026-12-12"]  # missing day kept, empty
    assert [i["activity"] for i in days[0]["items"]] == ["Reach by bus", "River rafting"]  # time order
    assert days[2]["items"] == []
    assert trip["itinerary"]["explanation"] == "College friends trip"
    assert trip["itinerary"]["budget_breakdown"] == {"activities": 1500.0}
    assert float(trip["budget"]) == 0  # budget is optional
    # It shows on the dashboard like any other trip.
    assert any(t["id"] == trip["id"] for t in client.get("/trips", headers=h).json())


def test_own_plan_downloads_as_pdf(client):
    h = auth(client)
    trip = client.post("/trips/own", json=OWN, headers=h).json()
    r = client.get(f"/trips/{trip['id']}/pdf", headers=h)
    assert r.status_code == 200 and r.content.startswith(b"%PDF")


def test_bad_time_is_refused(client):
    bad = {**OWN, "days": [{"items": [{"time": "25:00", "activity": "x"}]}]}
    assert client.post("/trips/own", json=bad, headers=auth(client)).status_code == 422


def test_edit_plan_replaces_the_days(client):
    h = auth(client)
    trip = client.post("/trips/own", json=OWN, headers=h).json()
    r = client.put(f"/trips/{trip['id']}/plan", headers=h, json={
        "days": [{"items": [{"time": "07:00", "activity": "Sunrise yoga", "estimated_cost": 500}]}],
        "notes": "Changed my mind",
    })
    assert r.status_code == 200, r.text
    it = r.json()["itinerary"]
    assert it["day_plan"][0]["items"][0]["activity"] == "Sunrise yoga"
    assert it["budget_breakdown"] == {"activities": 500.0} and it["explanation"] == "Changed my mind"


def test_an_ai_plan_can_be_edited_too(client):
    h = auth(client)
    trip = create_trip(client, {"destination": "Jaipur", "start_date": "2026-11-05", "end_date": "2026-11-06",
                                "budget": "20000", "travelers": 1, "style_tags": [], "use_memory": False}, h)
    before = trip["itinerary"]["budget_breakdown"]
    r = client.put(f"/trips/{trip['id']}/plan", headers=h,
                   json={"days": [{"items": [{"activity": "Amber Fort"}]}, {"items": []}]})
    assert r.status_code == 200
    assert r.json()["itinerary"]["budget_breakdown"] == before  # the AI's categories stay
    assert r.json()["source"] == "ai"


def test_only_the_owner_can_edit(client):
    trip = client.post("/trips/own", json=OWN, headers=auth(client)).json()
    r = client.put(f"/trips/{trip['id']}/plan", headers=auth(client, OTHER), json={"days": []})
    assert r.status_code == 404


def test_plan_again_on_new_dates(client):
    h = auth(client)
    trip = client.post("/trips/own", json=OWN, headers=h).json()
    client.post(f"/trips/{trip['id']}/packing", json={"name": "Rain jacket"}, headers=h)
    r = client.post(f"/trips/{trip['id']}/copy", json={"start_date": "2027-03-01"}, headers=h)
    assert r.status_code == 201, r.text
    new = r.json()
    assert new["id"] != trip["id"] and new["source"] == "copy"
    assert (new["start_date"], new["end_date"]) == ("2027-03-01", "2027-03-03")
    days = new["itinerary"]["day_plan"]
    assert [d["date"] for d in days] == ["2027-03-01", "2027-03-02", "2027-03-03"]
    assert days[0]["items"][1]["activity"] == "River rafting"
    names = [i["name"] for i in client.get(f"/trips/{new['id']}/packing", headers=h).json()["items"]]
    assert "Rain jacket" in names
    # The original is untouched.
    assert client.get(f"/trips/{trip['id']}", headers=h).json()["start_date"] == "2026-12-10"


def test_cannot_copy_someone_elses_trip(client):
    trip = client.post("/trips/own", json=OWN, headers=auth(client)).json()
    r = client.post(f"/trips/{trip['id']}/copy", json={"start_date": "2027-01-01"}, headers=auth(client, OTHER))
    assert r.status_code == 404


# --- what to take (or what was taken) -------------------------------------------

def _packing(client, trip_id, h):
    return {i["name"]: i for i in client.get(f"/trips/{trip_id}/packing", headers=h).json()["items"]}


def test_packing_items_are_saved_with_the_plan(client):
    h = auth(client)
    plan = {**OWN, "packing": [{"name": "Rain jacket", "category": "clothes", "quantity": 1},
                               {"name": "Aadhaar card", "category": "documents"},
                               {"name": "rain JACKET"}]}  # same item twice: kept once
    trip = client.post("/trips/own", json=plan, headers=h).json()
    items = _packing(client, trip["id"], h)
    assert items["Rain jacket"]["category"] == "clothes"
    assert "Aadhaar card" in items and sum(n.casefold() == "rain jacket" for n in items) == 1


def test_editing_the_packing_list_keeps_ticks(client):
    h = auth(client)
    trip = client.post("/trips/own", json={**OWN, "packing": [{"name": "Torch"}, {"name": "Cap"}]}, headers=h).json()
    torch = _packing(client, trip["id"], h)["Torch"]
    client.patch(f"/trips/{trip['id']}/packing/{torch['id']}", json={"packed_going": True}, headers=h)
    r = client.put(f"/trips/{trip['id']}/plan", headers=h, json={
        "days": [{"items": [{"activity": "Walk"}]}],
        "packing": [{"name": "Torch", "quantity": 2}, {"name": "Sunscreen", "category": "toiletries"}],
    })
    assert r.status_code == 200, r.text
    items = _packing(client, trip["id"], h)
    assert "Cap" not in items and "Sunscreen" in items
    assert items["Torch"]["quantity"] == 2 and items["Torch"]["packed_going"] is True


def test_edit_without_packing_leaves_the_list_alone(client):
    h = auth(client)
    trip = client.post("/trips/own", json={**OWN, "packing": [{"name": "Torch"}]}, headers=h).json()
    client.put(f"/trips/{trip['id']}/plan", headers=h, json={"days": [{"items": [{"activity": "Walk"}]}]})
    assert "Torch" in _packing(client, trip["id"], h)


# --- fill the rest (AI, or local rules without a key) -----------------------------

FILL = {**OWN, "destination": "Manali", "days": [
    {"items": [{"activity": "Snow day at Solang", "place": "", "time": ""}]},
    {"items": []}, {"items": []},
], "packing": [{"name": "Gloves"}]}


def test_fill_without_ai_uses_local_rules_and_keeps_my_words(client):
    h = auth(client)
    r = client.post("/trips/own/fill", json=FILL, headers=h)
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["source"] == "rules" and len(out["days"]) == 3
    assert out["days"][0]["items"][0]["activity"] == "Snow day at Solang"  # untouched
    assert out["days"][1]["items"] and out["days"][1]["items"][0]["activity"].startswith("Visit ")
    names = [p["name"] for p in out["packing"]]
    assert names and "Gloves" not in names  # never suggests what is already packed
    assert client.get("/trips", headers=h).json() == []  # nothing saved


def test_fill_with_ai_fills_blanks_but_never_overwrites(client, monkeypatch):
    import json as _json
    from app.core.config import settings
    from app.llm import plan_fill
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test")
    answer = {"days": [
        {"day": 1, "fill": [{"index": 0, "time": "08:00", "place": "Solang Valley", "estimated_cost": 3000}],
         "add": [{"time": "19:00", "activity": "Dinner on Mall Road", "place": "Mall Road", "estimated_cost": 800}]},
        {"day": 2, "add": [{"time": "09:00", "activity": "Hadimba Temple walk", "place": "Hadimba Temple"}]},
        {"day": 3, "add": [{"activity": "Snow day at Solang"}]},  # a duplicate of mine on another day is fine
    ], "packing": [{"name": "Thermal innerwear", "category": "clothes", "quantity": 2},
                   {"name": "gloves", "category": "accessories"}, {"name": "Weird", "category": "nonsense"}]}
    monkeypatch.setattr(plan_fill, "_call", lambda prompt: _json.dumps(answer))
    body = {**FILL, "days": [{"items": [{"activity": "Snow day at Solang", "time": "10:30", "place": ""}]},
                             {"items": []}, {"items": []}]}
    out = client.post("/trips/own/fill", json=body, headers=auth(client)).json()
    day1 = out["days"][0]["items"]
    mine = next(i for i in day1 if i["activity"] == "Snow day at Solang")
    assert mine["time"] == "10:30"  # theirs kept, the model's 08:00 ignored
    assert mine["place"] == "Solang Valley" and mine["estimated_cost"] == 3000  # blanks filled
    assert [i["activity"] for i in day1] == ["Snow day at Solang", "Dinner on Mall Road"]  # time order
    assert out["source"] == "ai" and out["added_items"] == 3 and out["filled_fields"] == 2
    assert {p["name"]: p["category"] for p in out["packing"]} == {"Thermal innerwear": "clothes", "Weird": "other"}


def test_fill_falls_back_when_the_model_answers_badly(client, monkeypatch):
    from app.core.config import settings
    from app.llm import plan_fill
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test")
    monkeypatch.setattr(plan_fill, "_call", lambda prompt: "sorry, no JSON")
    out = client.post("/trips/own/fill", json=FILL, headers=auth(client)).json()
    assert out["source"] == "rules" and out["days"][0]["items"][0]["activity"] == "Snow day at Solang"
