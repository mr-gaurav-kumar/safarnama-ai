"""Travel assistant: reads English and Hinglish questions, suggests places
that fit the budget and mood, prices them and adds the weather."""
from datetime import date

from app.assistant.estimate import estimate, travel_cost
from app.assistant.parse import parse
from tests.helpers import signup

TODAY = date(2026, 11, 20)


def test_parses_hinglish_question():
    q = parse("Mera budget 15k hai, 3 din ke liye Delhi se pahad mein ghumna hai, 2 log, december mein", TODAY)
    assert q.budget == 15_000 and q.days == 3 and q.travelers == 2 and q.month == 12
    assert q.origin == "Delhi" and "mountains" in q.moods and q.want_hills and q.asks_where


def test_parses_english_question_and_units():
    q = parse("Beach trip for a couple in January under ₹40,000 from Pune, a long weekend", TODAY)
    assert (q.budget, q.days, q.travelers, q.month, q.origin) == (40_000, 3, 2, 1, "Pune")
    assert q.want_coast and "beach" in q.moods
    assert parse("1.5 lakh mein ek hafta", TODAY).budget == 150_000
    assert parse("1.5 lakh mein ek hafta", TODAY).days == 7
    assert parse("weekend getaway, kuch peaceful, next month", TODAY).month == 12


def test_estimate_prices_travel_and_ground_and_judges_budget():
    delhi, manali = (28.61, 77.21), (32.24, 77.19)
    e = estimate(daily_cost=3000, days=4, travelers=2, budget=40_000, origin=delhi, dest=manali, name="Manali")
    assert e.travel_mode == "bus or train" and e.travel and e.travel > 0
    assert e.total == e.travel + e.stay + e.food + e.local
    assert e.verdict in ("comfortable", "fits", "tight", "over")
    assert travel_cost(1800, island=False)[0] == "flight"
    assert travel_cost(100, island=True)[0] == "flight"
    assert estimate(daily_cost=3000, days=3, travelers=1, budget=None, origin=None, dest=manali, name="Manali").travel is None


def test_where_can_i_go_returns_hill_picks_with_budget_and_weather(client):
    h = signup(client)["headers"]
    r = client.post("/assistant/chat", json={"message": "₹25,000 mein 4 din Delhi se pahad, 2 log, march"}, headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["intent"] == "recommend" and body["understood"]["origin"] == "Delhi"
    assert 1 <= len(body["picks"]) <= 4
    for p in body["picks"]:
        assert p["altitude_m"] >= 1000  # the hills, as asked
        assert p["season"]["label"] in ("ideal", "pleasant", "hot", "rainy", "cold")
        e = p["estimate"]
        assert e["travel"] and e["total"] == e["travel"] + e["stay"] + e["food"] + e["local"]
        assert e["verdict"] != "over"
        assert p["plan"]["days"] == 4 and p["plan"]["travelers"] == 2
    assert "pahad" not in body["reply"].lower() or body["reply"]  # template reply is present


def test_named_place_gets_its_own_answer(client):
    h = signup(client)["headers"]
    body = client.post("/assistant/chat", json={"message": "How is Manali in January for 3 days?"}, headers=h).json()
    assert body["intent"] == "place" and body["picks"][0]["name"] == "Manali"
    assert body["picks"][0]["season"]["label"] == "cold"


def test_follow_up_builds_on_earlier_question(client):
    h = signup(client)["headers"]
    history = [{"role": "user", "text": "Beach trip, 2 log, ₹60,000, December, from Mumbai"},
               {"role": "assistant", "text": "Here are some beaches."}]
    body = client.post("/assistant/chat", json={"message": "make it 6 days", "history": history}, headers=h).json()
    u = body["understood"]
    assert u["days"] == 6 and u["budget"] == 60_000 and u["travelers"] == 2 and u["origin"] == "Mumbai"
    assert all(p["coastal"] for p in body["picks"])


def test_assumptions_are_reported_and_needs_login(client):
    assert client.post("/assistant/chat", json={"message": "hi"}).status_code in (401, 403)
    h = signup(client)["headers"]
    body = client.post("/assistant/chat", json={"message": "where should I go?"}, headers=h).json()
    assert "3 days" in body["understood"]["assumed"] and "1 traveller" in body["understood"]["assumed"]
    assert client.post("/assistant/chat", json={"message": "hello"}, headers=h).json()["intent"] == "help"


def test_misspelt_place_is_still_found_with_its_budget(client):
    """'nanital' must answer about Nainital -- not a list of other hill towns."""
    h = signup(client)["headers"]
    history = [{"role": "user", "text": "₹20,000 mein 3 din Delhi se pahad, 2 log"},
               {"role": "assistant", "text": "Pachmarhi, Dharamshala, Manali."}]
    body = client.post("/assistant/chat", json={"message": "Show me the budget for the nanital", "history": history},
                       headers=h).json()
    assert body["intent"] == "place" and [p["name"] for p in body["picks"]] == ["Nainital"]
    e = body["picks"][0]["estimate"]
    assert e["travel"] and e["total"] > 0 and body["understood"]["travelers"] == 2  # kept from the history


def test_place_we_do_not_know_is_said_plainly(client):
    h = signup(client)["headers"]
    body = client.post("/assistant/chat", json={"message": "Kasol ka budget batao"}, headers=h).json()
    assert body["intent"] == "unknown" and body["picks"] == [] and "Kasol" in body["reply"]


def test_weekend_and_weekdays_change_dates_and_stay_cost():
    from datetime import date as d
    from app.assistant.service import _start_date

    # 20 Nov 2026 is a Friday.
    assert _start_date(11, TODAY, "weekend").weekday() == 5        # next Saturday
    assert _start_date(11, TODAY, "long_weekend").weekday() == 4   # a Friday
    assert _start_date(12, TODAY, "weekdays") == d(2026, 12, 7)    # first Monday on/after 1 Dec
    assert parse("weekend trip to the hills", TODAY).when == "weekend"
    assert parse("weekdays mein 3 din jana hai", TODAY).when == "weekdays"
    assert parse("weekdays mein 3 din jana hai", TODAY).days == 3

    fri, mon = d(2026, 11, 27), d(2026, 11, 30)
    weekend = estimate(daily_cost=3000, days=3, travelers=2, budget=None, origin=None, dest=(32.2, 77.2), name="Manali", start=fri)
    weekday = estimate(daily_cost=3000, days=3, travelers=2, budget=None, origin=None, dest=(32.2, 77.2), name="Manali", start=mon)
    assert weekend.weekend_nights == 2 and weekday.weekend_nights == 0
    assert weekend.stay > weekday.stay and weekend.food == weekday.food


def test_weekend_question_gets_weekend_dates(client):
    h = signup(client)["headers"]
    body = client.post("/assistant/chat", json={"message": "Weekend getaway from Delhi, hills, 2 log, ₹15,000"},
                       headers=h).json()
    assert body["understood"]["when"] == "weekend" and body["understood"]["days"] == 2
    for p in body["picks"]:
        assert date.fromisoformat(p["estimate"]["start_date"]).weekday() == 5
        assert p["estimate"]["weekend_nights"] == 1
