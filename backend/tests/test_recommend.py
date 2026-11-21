"""Budget Recommender (Phase 8, model #1)."""
from datetime import date, timedelta

from sqlalchemy import func, select

from app.ml import features
from app.ml.budget_recommender import MIN_FIT, recommend
from app.models.destination import DestinationFeature
from tests.helpers import auth, create_trip, verified

PARKS = {"Ranthambore", "Gir", "Bandhavgarh", "Kanha", "Jim Corbett", "Kaziranga"}


def ask(client, headers, **body):
    payload = {"budget": "40000", "days": 4, "travelers": 2, **body}
    r = client.post("/recommend/budget", json=payload, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def test_needs_a_login_and_valid_input(client):
    assert client.post("/recommend/budget", json={"budget": "1000", "days": 2}).status_code == 401
    h = auth(client)
    bad = [{"budget": "0", "days": 2}, {"budget": "1000", "days": 0},
           {"budget": "1000", "days": 2, "month": 13},
           {"budget": "1000", "days": 2, "style_tags": ["food", "food"]},
           {"budget": "1000", "days": 2, "style_tags": ["shopping"]}]
    for body in bad:
        assert client.post("/recommend/budget", json=body, headers=h).status_code == 422, body


def test_budget_maths_and_everything_returned_is_affordable(client):
    out = ask(client, auth(client))
    assert out["per_person_per_day"] == 5000          # 40,000 / 2 people / 4 days
    assert out["on_ground_per_day"] == 3750           # a quarter set aside for getting there
    assert out["considered"] == len(features.DESTINATIONS)
    assert 1 <= len(out["items"]) <= 6
    for item in out["items"]:
        assert item["daily_cost"] * MIN_FIT <= 3750
        assert item["reasons"]
    scores = [i["score"] for i in out["items"]]
    assert scores == sorted(scores, reverse=True)
    assert "curated" in out["note"]


def test_a_small_budget_leaves_out_expensive_places(client):
    out = ask(client, auth(client), budget="8000", days=4, travelers=2, limit=20)
    names = {i["name"] for i in out["items"]}
    assert out["over_budget"] > 0
    assert not names & {"Havelock", "Port Blair", "Kanha", "Bandhavgarh", "Leh"}
    assert all(i["daily_cost"] <= 1000 / MIN_FIT for i in out["items"])


def test_styles_steer_the_ranking(client):
    h = auth(client)
    wild = ask(client, h, budget="200000", style_tags=["adventure", "nature"], use_memory=False)
    city = ask(client, h, budget="200000", style_tags=["culture", "food"], use_memory=False)
    assert wild["items"][0]["styles"]["nature"] >= 0.9
    assert city["items"][0]["styles"]["culture"] >= 0.8 and city["items"][0]["styles"]["food"] >= 0.8
    assert wild["items"][0]["name"] != city["items"][0]["name"]


def test_parks_are_left_out_while_closed_and_seasons_are_given(client):
    h = auth(client)
    out = ask(client, h, budget="500000", month=8, style_tags=["nature"], limit=20)
    assert not {i["name"] for i in out["items"]} & PARKS
    assert out["closed"] == len(PARKS)
    assert all(i["season"] in ("ideal", "pleasant", "hot", "rainy", "cold") for i in out["items"])
    assert any("August" in r for r in out["items"][0]["reasons"])
    # Same request in February: parks are back.
    feb = ask(client, h, budget="500000", month=2, style_tags=["nature"], limit=20)
    assert {i["name"] for i in feb["items"]} & PARKS


def test_the_month_moves_monsoon_places_down(client):
    h = auth(client)
    body = dict(budget="200000", style_tags=["relax"], use_memory=False, limit=20)
    jan = [i["name"] for i in ask(client, h, month=1, **body)["items"]]
    jul = [i["name"] for i in ask(client, h, month=7, **body)["items"]]
    assert "Goa" in jan and ("Goa" not in jul or jul.index("Goa") > jan.index("Goa"))


def test_rated_trips_shape_the_taste(client, db_session):
    me = verified(client)
    h = me["headers"]
    past = date.today() - timedelta(days=40)
    loved = create_trip(client, {
        "destination": "Rishikesh", "start_date": past.isoformat(),
        "end_date": (past + timedelta(days=2)).isoformat(), "budget": "20000",
        "travelers": 1, "style_tags": ["adventure"], "use_memory": False,
    }, h)
    assert client.put(f"/trips/{loved['id']}/feedback", json={"rating": 5}, headers=h).status_code == 200

    plain = ask(client, h, budget="200000", use_memory=False, limit=20)
    personal = ask(client, h, budget="200000", limit=20)
    assert personal["taste"] == ["You liked Rishikesh (5/5)"]
    assert plain["taste"] == []

    def adventure_share(out):
        top = out["items"][:5]
        return sum(i["styles"]["adventure"] for i in top) / len(top)
    assert adventure_share(personal) > adventure_share(plain)
    # Somewhere they have been already is still listed, but marked and moved down.
    import uuid as _uuid

    everything = recommend(db_session, budget=200000, days=4, travelers=2, style_tags=["adventure"],
                           user_id=_uuid.UUID(me["user"]["id"]), limit=100)["items"]
    rishikesh = next(i for i in everything if i["name"] == "Rishikesh")
    assert rishikesh["visited"] and "You have been here before" in rishikesh["reasons"]
    assert not any(i["visited"] for i in everything if i["name"] != "Rishikesh")


def test_seeding_happens_once_and_edits_stick(db_session):
    assert features.ensure_seeded(db_session) == len(features.DESTINATIONS)
    assert features.ensure_seeded(db_session) == 0
    goa = db_session.scalar(select(DestinationFeature).where(DestinationFeature.name == "Goa"))
    goa.daily_cost = 99999
    db_session.commit()
    features.ensure_seeded(db_session)
    assert db_session.scalar(select(func.count()).select_from(DestinationFeature)) == len(features.DESTINATIONS)
    out = recommend(db_session, budget=1_000_000, days=2, travelers=1, style_tags=["relax"], limit=40)
    assert next(i for i in out["items"] if i["name"] == "Goa")["daily_cost"] == 99999


def test_matching_free_text_to_a_destination(db_session):
    rows = features.all_destinations(db_session)
    m = lambda text: (features.match(rows, text) or type("x", (), {"name": None})).name  # noqa: E731
    assert m("Fort Kochi") == "Kochi"
    assert m("weekend in pondicherry") == "Puducherry"
    assert m("Leh-Ladakh") == "Leh"
    assert m("GOA") == "Goa"
    assert m("Atlantis") is None


# --- From and To -------------------------------------------------------------

def _ask(client, h, **extra):
    body = {"budget": 30000, "days": 4, "travelers": 2, "month": 3, "style_tags": [], "use_memory": False, "limit": 20}
    r = client.post("/recommend/budget", json={**body, **extra}, headers=h)
    assert r.status_code == 200, r.text
    return r.json()


def test_from_prices_each_place_from_where_you_start(client):
    from tests.helpers import signup
    h = signup(client)["headers"]
    data = _ask(client, h, origin="Delhi, Delhi")
    assert data["origin"] == "Delhi" and data["origin_found"]
    names = [i["name"] for i in data["items"]]
    assert "Delhi" not in names  # not a trip from your own city
    for i in data["items"]:
        assert i["distance_km"] and i["travel_mode"] and i["travel_fare"] > 0
        e = i["estimate"]
        assert e["total"] == e["travel"] + e["stay"] + e["food"] + e["local"]
    # Nearer places keep more money for the ground than far ones.
    agra = next(i for i in data["items"] if i["name"] == "Agra")
    far = [i for i in data["items"] if i["distance_km"] > 1500]
    assert all(agra["travel_fare"] < f["travel_fare"] for f in far)


def test_to_a_place_lists_it_first_with_its_neighbours(client):
    from tests.helpers import signup
    h = signup(client)["headers"]
    data = _ask(client, h, origin="Delhi", destination="manaali")  # typo on purpose
    assert data["destination_mode"] == "place" and data["items"][0]["name"] == "Manali"
    assert data["items"][0]["is_destination"]
    assert all(i["state"] in ("Himachal Pradesh", "Punjab", "Jammu and Kashmir", "Uttarakhand", "Ladakh") or
               i["distance_km"] is not None for i in data["items"])
    assert all(not i["is_destination"] for i in data["items"][1:])


def test_to_a_state_keeps_only_that_state(client):
    from tests.helpers import signup
    h = signup(client)["headers"]
    data = _ask(client, h, origin="Mumbai", destination="Kerala")
    assert data["destination_mode"] == "state" and data["items"]
    assert {i["state"] for i in data["items"]} == {"Kerala"}


def test_unknown_to_falls_back_to_everywhere(client):
    from tests.helpers import signup
    h = signup(client)["headers"]
    data = _ask(client, h, origin="Delhi", destination="Atlantis")
    assert data["destination_mode"] == "not_found" and "Atlantis" in data["destination_note"] and data["items"]


def test_short_trip_far_away_moves_down(client):
    from tests.helpers import signup
    h = signup(client)["headers"]
    data = _ask(client, h, origin="Delhi", days=2, budget=60000)
    far = [i for i in data["items"] if i["distance_km"] * 1.25 > 700]
    assert all(any("long journey" in r.lower() for r in i["reasons"]) for i in far)
