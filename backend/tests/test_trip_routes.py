import pytest

from tests.helpers import OTHER, SIGNUP, auth, create_trip

TRIP = {
    "destination": "Goa",
    "start_date": "2026-10-01",
    "end_date": "2026-10-03",
    "budget": "25000",
    "travelers": 2,
    "style_tags": ["relax", "food"],
    "use_memory": True,
}


def test_create_returns_at_once_with_status_processing(client):
    """202 and no itinerary yet: the request must never wait on the planner."""
    h = auth(client, SIGNUP)
    r = client.post("/trips", json=TRIP, headers=h)
    assert r.status_code == 202
    body = r.json()
    assert body["status"] == "processing"
    assert body["itinerary"] is None


def test_the_background_job_completes_the_trip(client):
    h = auth(client, SIGNUP)
    trip = create_trip(client, TRIP, h)
    assert trip["status"] == "completed"
    assert len(trip["itinerary"]["day_plan"]) == 3, "1 Oct to 3 Oct is three days"
    assert set(trip["itinerary"]["budget_breakdown"]) == {"stay", "food", "travel", "misc"}


def test_budget_breakdown_does_not_exceed_the_budget(client):
    h = auth(client, SIGNUP)
    trip = create_trip(client, TRIP, h)
    assert sum(trip["itinerary"]["budget_breakdown"].values()) <= float(TRIP["budget"])


def test_trips_are_listed_newest_first_and_scoped_to_the_owner(client):
    h = auth(client, SIGNUP)
    create_trip(client, TRIP, h)
    create_trip(client, {**TRIP, "destination": "Manali"}, h)

    mine = client.get("/trips", headers=h).json()
    assert [t["destination"] for t in mine] == ["Manali", "Goa"]

    theirs = client.get("/trips", headers=auth(client, OTHER)).json()
    assert theirs == [], "another user must not see these trips"


def test_one_user_cannot_read_or_delete_another_users_trip(client):
    mine = auth(client, SIGNUP)
    trip_id = create_trip(client, TRIP, mine)["id"]

    theirs = auth(client, OTHER)
    assert client.get(f"/trips/{trip_id}", headers=theirs).status_code == 404
    assert client.delete(f"/trips/{trip_id}", headers=theirs).status_code == 404
    assert client.get(f"/trips/{trip_id}", headers=mine).status_code == 200


def test_delete_removes_the_trip(client):
    h = auth(client, SIGNUP)
    trip_id = create_trip(client, TRIP, h)["id"]
    assert client.delete(f"/trips/{trip_id}", headers=h).status_code == 204
    assert client.get(f"/trips/{trip_id}", headers=h).status_code == 404


def test_a_crashing_generator_leaves_the_trip_failed_not_stuck(client, monkeypatch):
    """If generation blows up, the trip must end 'failed' with a readable
    message -- never sit on 'processing' forever."""
    from app.services import trip_service

    def boom(*_a, **_k):
        raise RuntimeError("model exploded")

    monkeypatch.setattr(trip_service, "generate_itinerary", boom)
    h = auth(client, SIGNUP)
    trip = create_trip(client, TRIP, h)
    assert trip["status"] == "failed"
    assert trip["error"] and "exploded" not in trip["error"], "internals must not leak to the user"


def test_trips_require_a_token(client):
    assert client.get("/trips").status_code == 401
    assert client.post("/trips", json=TRIP).status_code == 401


@pytest.mark.parametrize(
    "override, why",
    [
        ({"end_date": "2026-09-30"}, "end before start"),
        ({"budget": "0"}, "zero budget"),
        ({"travelers": 0}, "no travellers"),
        ({"style_tags": ["relax", "relax"]}, "repeated tag"),
        ({"style_tags": ["nightlife"]}, "tag outside the allowed set"),
        ({"end_date": "2026-12-31"}, "longer than the 30-day limit"),
    ],
)
def test_invalid_trips_are_rejected(client, override, why):
    h = auth(client, SIGNUP)
    r = client.post("/trips", json={**TRIP, **override}, headers=h)
    assert r.status_code == 422, f"should reject: {why}"
