"""Map coordinates: right pins, no wrong-city pins, no crash when offline, and
Nominatim's rules (cache, one request a second) respected."""
import httpx
import pytest

from app.core.config import settings
from app.geo import geocode as geo
from app.geo.itinerary_map import add_coordinates

JAIPUR = {"lat": "26.9124", "lon": "75.7873"}
HAWA_MAHAL = {"lat": "26.9239", "lon": "75.8267"}
CITY_PALACE_UDAIPUR = {"lat": "24.5764", "lon": "73.6835"}  # ~270 km from Jaipur


@pytest.fixture
def fake_nominatim(monkeypatch):
    from app.core import cache

    monkeypatch.setattr(settings, "GEOCODING_ENABLED", True)
    monkeypatch.setattr(cache, "_cache", cache.MemoryCache())
    monkeypatch.setattr(geo, "_throttle", lambda: None)

    answers = {
        "Jaipur, India": [JAIPUR],
        "Hawa Mahal, Jaipur, India": [HAWA_MAHAL],
        "City Palace, Jaipur, India": [CITY_PALACE_UDAIPUR],  # a wrong match
        "Nowhere Cafe, Jaipur, India": [],
    }
    calls = []

    def fetch(query):
        calls.append(query)
        return answers.get(query, [])

    monkeypatch.setattr(geo, "_fetch", fetch)
    return calls


def plan(*places):
    return [{"day": 1, "date": "2026-11-05",
             "items": [{"time": "09:00", "place": p, "activity": "x", "estimated_cost": 0} for p in places]}]


def pins(day_plan):
    return {i["place"]: (i.get("lat"), i.get("lng")) for d in day_plan for i in d["items"]}


def test_places_get_coordinates(fake_nominatim):
    out = pins(add_coordinates("Jaipur", plan("Hawa Mahal")))
    assert out["Hawa Mahal"] == (26.9239, 75.8267)


def test_a_same_named_place_in_another_city_is_left_off(fake_nominatim):
    """"City Palace" resolving to Udaipur must not put a pin 270 km away."""
    out = pins(add_coordinates("Jaipur", plan("Hawa Mahal", "City Palace")))
    assert out["City Palace"] == (None, None)
    assert out["Hawa Mahal"][0] is not None


def test_the_destination_itself_is_pinned_at_its_centre(fake_nominatim):
    out = pins(add_coordinates("Jaipur", plan("Jaipur")))
    assert out["Jaipur"] == (26.9124, 75.7873)


def test_each_place_is_looked_up_once_and_then_cached(fake_nominatim):
    add_coordinates("Jaipur", plan("Hawa Mahal", "Hawa Mahal"))
    add_coordinates("Jaipur", plan("Hawa Mahal"))
    assert fake_nominatim.count("Hawa Mahal, Jaipur, India") == 1
    assert fake_nominatim.count("Jaipur, India") == 1


def test_misses_are_cached_too(fake_nominatim):
    add_coordinates("Jaipur", plan("Nowhere Cafe"))
    add_coordinates("Jaipur", plan("Nowhere Cafe"))
    assert fake_nominatim.count("Nowhere Cafe, Jaipur, India") == 1


def test_offline_returns_the_plan_unchanged(monkeypatch):
    from app.core import cache

    monkeypatch.setattr(settings, "GEOCODING_ENABLED", True)
    monkeypatch.setattr(cache, "_cache", cache.MemoryCache())
    monkeypatch.setattr(geo, "_throttle", lambda: None)
    calls = []

    def down(query):
        calls.append(query)
        raise httpx.ConnectError("no network")

    monkeypatch.setattr(geo, "_fetch", down)
    original = plan("Hawa Mahal", "City Palace", "Amer Fort")
    out = add_coordinates("Jaipur", original)
    assert out == original
    assert len(calls) == 1, "stop at the first failure -- no timeout per place"


def test_the_input_plan_is_not_mutated(fake_nominatim):
    original = plan("Hawa Mahal")
    add_coordinates("Jaipur", original)
    assert "lat" not in original[0]["items"][0]


def test_requests_are_spaced_at_least_a_second_apart(monkeypatch):
    """Nominatim allows one request per second."""
    slept = []
    monkeypatch.setattr(geo.time, "sleep", lambda s: slept.append(s))
    monkeypatch.setattr(geo, "_last_request_at", geo.time.monotonic())
    geo._throttle()
    assert slept and slept[0] >= 1.0


def test_distance_is_roughly_right():
    jaipur = geo.Point(26.9124, 75.7873)
    delhi = geo.Point(28.6139, 77.2090)
    assert 230 < geo.distance_km(jaipur, delhi) < 250  # ~236 km as the crow flies


def test_the_trip_job_writes_coordinates_into_the_itinerary(client, fake_nominatim):
    from tests.helpers import auth, create_trip

    h = auth(client)
    trip = create_trip(client, {
        "destination": "Jaipur", "start_date": "2026-11-05", "end_date": "2026-11-05",
        "budget": "20000", "travelers": 2, "style_tags": [], "use_memory": False,
    }, h)
    first = trip["itinerary"]["day_plan"][0]["items"][0]
    assert (first["lat"], first["lng"]) == (26.9124, 75.7873)
