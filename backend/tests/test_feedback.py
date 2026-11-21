"""Rating a finished trip, and ratings steering memory (the feedback loop)."""
from datetime import date, timedelta

from app.models.embedding import TripEmbedding
from tests.helpers import SIGNUP, create_trip, verified


def trip(dest, start: date, days=3, tags=("relax", "food")):
    return {
        "destination": dest, "start_date": start.isoformat(),
        "end_date": (start + timedelta(days=days - 1)).isoformat(),
        "budget": "30000", "travelers": 2, "style_tags": list(tags), "use_memory": True,
    }


PAST = date.today() - timedelta(days=60)
FUTURE = date.today() + timedelta(days=30)


def test_cannot_rate_before_the_trip_is_over(client):
    me = verified(client)
    t = create_trip(client, trip("Goa", FUTURE), me["headers"])
    assert client.get(f"/trips/{t['id']}/feedback", headers=me["headers"]).json()["can_rate"] is False
    r = client.put(f"/trips/{t['id']}/feedback", json={"rating": 5}, headers=me["headers"])
    assert r.status_code == 409


def test_rate_then_change_your_mind(client):
    me = verified(client)
    t = create_trip(client, trip("Goa", PAST), me["headers"])
    r = client.put(f"/trips/{t['id']}/feedback", json={"rating": 4, "comment": "lovely"}, headers=me["headers"])
    assert r.status_code == 200 and r.json()["mine"] == {"rating": 4, "comment": "lovely"}
    r = client.put(f"/trips/{t['id']}/feedback", json={"rating": 2}, headers=me["headers"])
    assert r.json()["mine"]["rating"] == 2 and r.json()["count"] == 1
    listed = client.get("/trips", headers=me["headers"]).json()[0]
    assert listed["my_rating"] == 2


def test_ratings_outside_one_to_five_are_rejected(client):
    me = verified(client)
    t = create_trip(client, trip("Goa", PAST), me["headers"])
    for bad in (0, 6):
        assert client.put(f"/trips/{t['id']}/feedback", json={"rating": bad}, headers=me["headers"]).status_code == 422


def test_the_rating_is_written_into_memory(client, db_session):
    me = verified(client)
    t = create_trip(client, trip("Goa", PAST), me["headers"])
    client.put(f"/trips/{t['id']}/feedback", json={"rating": 2, "comment": "too crowded"}, headers=me["headers"])
    db_session.expire_all()
    row = db_session.query(TripEmbedding).one()
    assert row.rating == 2
    assert "rated it 2/5" in row.source_text and "too crowded" in row.source_text


def test_a_loved_trip_outranks_a_disliked_one_that_is_just_as_similar(client, monkeypatch):
    """Two near-identical past Goa trips; the one rated 5 must come first, and
    the planner must be told about the one rated 1."""
    from app.services import trip_service

    me = verified(client)
    loved = create_trip(client, trip("Goa", PAST), me["headers"])
    hated = create_trip(client, trip("Goa", PAST - timedelta(days=30)), me["headers"])
    client.put(f"/trips/{loved['id']}/feedback", json={"rating": 5}, headers=me["headers"])
    client.put(f"/trips/{hated['id']}/feedback", json={"rating": 1, "comment": "rained, dull"}, headers=me["headers"])

    seen = {}
    real = trip_service.generate_itinerary
    monkeypatch.setattr(trip_service, "generate_itinerary", lambda **kw: (seen.update(kw), real(**kw))[1])
    new = create_trip(client, trip("Goa", FUTURE), me["headers"])

    sources = new["itinerary"]["memory_sources"]
    assert [s["trip_id"] for s in sources[:2]] == [loved["id"], hated["id"]]
    assert "rated it 1/5" in seen["memory_context"] and "rained, dull" in seen["memory_context"]


def test_a_members_rating_does_not_change_the_owners_memory(client, db_session):
    from tests.helpers import OTHER, invite_token

    garv = verified(client, SIGNUP)
    riya = verified(client, OTHER)
    t = create_trip(client, trip("Goa", PAST), garv["headers"])
    client.post(f"/trips/{t['id']}/invite", json={"email": OTHER["email"]}, headers=garv["headers"])
    client.post(f"/trips/{t['id']}/join", json={"token": invite_token(OTHER["email"])}, headers=riya["headers"])

    assert client.put(f"/trips/{t['id']}/feedback", json={"rating": 1}, headers=riya["headers"]).status_code == 200
    db_session.expire_all()
    assert db_session.query(TripEmbedding).one().rating is None
    summary = client.get(f"/trips/{t['id']}/feedback", headers=garv["headers"]).json()
    assert summary["count"] == 1 and summary["mine"] is None
