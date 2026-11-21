"""Think on the Plan (Phase 8, model #2): the season model, the reasoning it
produces, and how that reaches the progress stream, the prompt and the plan."""
from collections import Counter
from datetime import date, timedelta

from app.core.config import settings
from app.ml import season
from app.ml.think import think_about_trip
from app.realtime import progress
from app.services import trip_service
from tests.helpers import auth, create_trip


def think(db, dest, start, days=3, budget=30000, travelers=2, tags=()):
    return think_about_trip(db, destination=dest, start_date=start,
                            end_date=start + timedelta(days=days - 1),
                            budget=budget, travelers=travelers, style_tags=list(tags))


# --- the season model ------------------------------------------------------------

def test_season_model_generalises_to_places_it_has_not_seen():
    """Grouped CV: every fold holds out whole destinations. It must beat
    knowing only the month (the majority label for each month)."""
    from sklearn.model_selection import GroupKFold

    X, y, groups = season.training_set()
    right = baseline = 0
    for train, test in GroupKFold(n_splits=5).split(X, y, groups):
        from sklearn.ensemble import RandomForestClassifier

        model = RandomForestClassifier(n_estimators=100, random_state=0).fit([X[i] for i in train], [y[i] for i in train])
        pred = model.predict([X[i] for i in test])
        right += sum(p == y[i] for p, i in zip(pred, test))
        by_month = {}
        for i in train:
            by_month.setdefault((round(X[i][4], 6), round(X[i][5], 6)), Counter())[y[i]] += 1
        baseline += sum(by_month[(round(X[i][4], 6), round(X[i][5], 6))].most_common(1)[0][0] == y[i] for i in test)
    accuracy, base = right / len(y), baseline / len(y)
    assert accuracy >= 0.85, accuracy
    assert accuracy > base + 0.2, (accuracy, base)


def test_season_model_knows_the_obvious_cases():
    assert season.predict(15.30, 74.12, 10, True, 7)[0] == "rainy"      # Goa, July
    assert season.predict(34.15, 77.58, 3500, False, 1)[0] == "cold"    # Leh, January
    assert season.predict(26.91, 75.79, 430, False, 5)[0] == "hot"      # Jaipur, May
    assert season.predict(11.94, 79.81, 5, True, 11)[0] == "rainy"      # Puducherry, November
    label, conf = season.predict(26.91, 75.79, 430, False, 12)          # Jaipur, December
    assert label == "ideal" and 0.5 < conf <= 1.0


# --- the reasoning -------------------------------------------------------------------

def test_monsoon_goa(db_session):
    t = think(db_session, "Goa", date(2026, 7, 10), tags=["relax"])
    assert t["place"]["name"] == "Goa" and t["place"]["how"] == "matched"
    assert t["seasons"][0]["label"] == "rainy"
    assert "monsoon" in t["headline"] and t["headline"].startswith("July on the west coast")
    assert t["crowd"] == "quiet"
    assert any("indoor or covered backup" in n for n in t["prompt_notes"])


def test_christmas_week_is_busy(db_session):
    t = think(db_session, "Fort Kochi", date(2026, 12, 28), days=6)
    assert t["crowd"] == "busy"
    assert any("Christmas" in x for x in t["thoughts"])
    assert [s["month"] for s in t["seasons"]] == [12, 1], "a trip over New Year covers both months"


def test_closed_park_is_called_out(db_session):
    t = think(db_session, "Ranthambore", date(2026, 8, 1), budget=100000)
    assert any("usually closed in August" in x for x in t["thoughts"])
    assert any("safari" in n for n in t["prompt_notes"])


def test_budget_verdicts(db_session):
    tight = think(db_session, "Goa", date(2026, 12, 1), days=4, budget=10000, travelers=2)
    rich = think(db_session, "Goa", date(2026, 12, 1), days=4, budget=200000, travelers=2)
    assert tight["budget"]["verdict"] == "tight" and rich["budget"]["verdict"] == "generous"
    assert tight["budget"]["per_person_per_day"] == 1250 and tight["budget"]["typical"] == 4000


def test_style_fit(db_session):
    t = think(db_session, "Leh", date(2026, 7, 1), tags=["adventure", "food"])
    assert t["style"] == {"strong": ["adventure"], "weak": ["food"]}


def test_unknown_town_in_a_known_state_borrows_a_neighbour(db_session):
    t = think(db_session, "Kasol, Himachal Pradesh", date(2026, 5, 20))
    assert t["place"]["how"] == "state" and t["place"]["state"] == "Himachal Pradesh"
    assert "rough guide" in t["thoughts"][0]
    assert any("school holidays" in x for x in t["thoughts"])


def test_nearby_by_map_when_geocoding_is_on(db_session, monkeypatch):
    from app.geo import geocode as geo

    monkeypatch.setattr(settings, "GEOCODING_ENABLED", True)
    monkeypatch.setattr(geo, "geocode", lambda q: geo.Point(32.03, 77.35))  # Kasol
    t = think(db_session, "Kasol", date(2026, 10, 5))
    assert t["place"] == {**t["place"], "name": "Manali", "how": "nearby"}


def test_nowhere_known_skips_the_place_checks(db_session):
    t = think(db_session, "Atlantis", date(2026, 3, 3))
    assert t["place"] is None and t["seasons"] == [] and t["budget"]["verdict"] is None
    assert "couldn't place" in t["thoughts"][0]


# --- wired into planning -----------------------------------------------------------------

def test_a_planned_trip_shows_and_keeps_its_thinking(client, monkeypatch):
    seen = {}
    real = trip_service.generate_itinerary
    monkeypatch.setattr(trip_service, "generate_itinerary", lambda **kw: (seen.update(kw), real(**kw))[1])

    h = auth(client)
    trip = create_trip(client, {
        "destination": "Goa", "start_date": "2026-07-10", "end_date": "2026-07-12",
        "budget": "30000", "travelers": 2, "style_tags": ["relax"], "use_memory": True,
    }, h)
    thinking = trip["itinerary"]["thinking"]
    assert thinking["place"]["name"] == "Goa" and thinking["thoughts"]
    assert "indoor or covered backup" in seen["thinking_context"]

    history = list(progress.get_broker()._history[progress.channel_for(trip["id"])])
    event = next(e for e in history if e.get("step") == "thinking")
    assert event["message"] == thinking["headline"] and event["thoughts"] == thinking["thoughts"]


def test_the_notes_reach_the_real_prompt():
    from app.llm.itinerary import _build_prompt

    prompt = _build_prompt(destination="Goa", start_date=date(2026, 7, 1), end_date=date(2026, 7, 2),
                           days=2, budget=1000, travelers=1, style_tags=[], memory_context=None,
                           thinking_context="It is monsoon: plan indoors.")
    assert "Planner's notes" in prompt and "It is monsoon: plan indoors." in prompt


def test_a_thinking_failure_never_stops_the_plan(client, monkeypatch):
    import app.ml.think as think_mod

    def boom(*a, **k):
        raise RuntimeError("model file missing")
    monkeypatch.setattr(think_mod, "think_about_trip", boom)
    h = auth(client)
    trip = create_trip(client, {"destination": "Goa", "start_date": "2026-12-01", "end_date": "2026-12-02",
                                "budget": "20000", "travelers": 1}, h)
    assert trip["status"] == "completed" and trip["itinerary"]["thinking"] is None


def test_preview_endpoint(client):
    h = auth(client)
    r = client.post("/recommend/think", json={"destination": "Leh", "start_date": "2027-01-10",
                                              "end_date": "2027-01-12", "budget": "50000"}, headers=h)
    assert r.status_code == 200 and r.json()["seasons"][0]["label"] == "cold"
    assert client.post("/recommend/think", json={"destination": "Leh", "start_date": "2027-01-10",
                                                 "end_date": "2027-01-01", "budget": "5"}, headers=h).status_code == 422
