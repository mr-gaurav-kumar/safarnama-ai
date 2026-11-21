"""Official tourism data: internally consistent, correctly matched to
destinations, and actually reaching the planner."""
import pytest

from app.data import tourism


# --- the numbers hang together -------------------------------------------------

def test_monthly_arrivals_add_up_to_the_published_total():
    assert sum(tourism.FTA_MONTHLY_2025_LAKH) == pytest.approx(tourism.FTA_TOTAL_2025_LAKH, abs=0.1)
    assert len(tourism.FTA_MONTHLY_2025_LAKH) == 12


@pytest.mark.parametrize("rows, total", [
    (tourism.DTV_BY_STATE_2024_M, tourism.DTV_TOTAL_2024_M),
    (tourism.FTV_BY_STATE_2024_M, tourism.FTV_TOTAL_2024_M),
])
def test_state_rankings_are_sorted_and_within_the_national_total(rows, total):
    values = [v for _, v in rows]
    assert values == sorted(values, reverse=True), "a ranking must be in rank order"
    assert sum(values) < total


def test_every_ranked_state_is_a_real_state_or_ut():
    for name, _ in tourism.DTV_BY_STATE_2024_M + tourism.FTV_BY_STATE_2024_M:
        assert name in tourism.STATES_AND_UTS


def test_every_city_maps_to_a_real_state_or_ut():
    assert set(tourism.CITY_TO_STATE.values()) <= set(tourism.STATES_AND_UTS)


# --- destination matching -------------------------------------------------------

@pytest.mark.parametrize("destination, state", [
    ("Jaipur", "Rajasthan"),
    ("jaipur, rajasthan", "Rajasthan"),
    ("Old Manali", "Himachal Pradesh"),
    ("Rann of Kutch", "Gujarat"),
    ("Madhya Pradesh wildlife loop", "Madhya Pradesh"),
    ("North Goa", "Goa"),
    ("Leh", "Ladakh"),
    ("Paris", None),
    ("Pune", "Maharashtra"),
])
def test_destinations_map_to_their_state(destination, state):
    assert tourism.state_for(destination) == state


def test_a_word_inside_another_word_does_not_match():
    """'Goa' must not match 'Goalpara'; matching is on whole words."""
    assert tourism.state_for("Goalpara") is None


# --- the context line -------------------------------------------------------------

def test_context_names_the_state_rank_and_season():
    line = tourism.context_for_trip("Agra", 12)
    assert "Uttar Pradesh in 2024" in line
    assert "#1 among states" in line
    assert "Dec" in line and "peak season" in line


def test_context_for_an_unranked_state_still_gives_the_season():
    line = tourism.context_for_trip("Goa", 5)
    assert "Goa in 2024" not in line
    assert "May" in line and "off season" in line


def test_the_planner_receives_the_official_figures(client, monkeypatch):
    from app.services import trip_service
    from tests.helpers import auth, create_trip

    seen = {}
    real = trip_service.generate_itinerary

    def spy(**kwargs):
        seen.update(kwargs)
        return real(**kwargs)

    monkeypatch.setattr(trip_service, "generate_itinerary", spy)
    create_trip(client, {
        "destination": "Jaipur", "start_date": "2026-11-05", "end_date": "2026-11-06",
        "budget": "20000", "travelers": 2, "style_tags": [], "use_memory": False,
    }, auth(client))
    assert "Rajasthan in 2024" in seen["govt_context"]
    assert "Nov" in seen["govt_context"]


# --- the endpoint -----------------------------------------------------------------

def test_insights_endpoint_is_public_and_cites_every_series(client):
    r = client.get("/insights")
    assert r.status_code == 200
    body = r.json()
    for key in ("foreign_arrivals_by_month", "domestic_visits_by_state",
                "foreign_visits_by_state", "top_monuments", "foreign_arrivals_by_year",
                "forex_earnings_by_year", "departures_by_year", "source_countries_2024",
                "source_countries_2025", "purpose_of_visit", "ports_of_entry", "key_facts",
                "year_on_year"):
        series = body[key]
        assert series["rows"], f"{key} is empty"
        assert series["sources"] and all(s["url"].startswith("https://") for s in series["sources"])
    assert body["headline"]["peak_month"] == "Dec"
    assert body["headline"]["quietest_month"] == "May"
    assert "max-age" in r.headers["cache-control"]
    assert body["reports"] and all(rep["url"].startswith("https://") for rep in body["reports"])
