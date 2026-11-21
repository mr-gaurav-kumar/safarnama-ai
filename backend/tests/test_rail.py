"""Live train search -- the API is faked; only our handling is tested."""
from datetime import date, timedelta

from tests.helpers import signup

SAMPLE = {
    "status": True,
    "data": [{
        "train_number": "12952", "train_name": "MUMBAI RAJDHANI", "from": "NDLS", "to": "MMCT",
        "from_station_name": "NEW DELHI", "to_station_name": "MUMBAI CENTRAL",
        "from_std": "16:55", "to_sta": "08:35", "to_day": 1, "duration": "15:40",
        "class_type": ["1A", "2A", "3A"], "run_days": ["Mon", "Tue"], "train_type": "RAJ",
    }],
}


def test_off_without_a_key(client, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "RAPIDAPI_KEY", "")
    assert client.get("/rail/status").json() == {"live_search": False}
    h = signup(client)["headers"]
    r = client.get("/rail/trains", params={"from": "NDLS", "to": "MMCT", "date": date.today().isoformat()}, headers=h)
    assert r.status_code == 503


def test_trains_are_normalised(client, monkeypatch):
    from app.core.config import settings
    from app.rail import irctc
    monkeypatch.setattr(settings, "RAPIDAPI_KEY", "test-key")
    calls = []
    monkeypatch.setattr(irctc, "_get", lambda path, params: calls.append(path) or SAMPLE)
    h = signup(client)["headers"]
    day = (date.today() + timedelta(days=5)).isoformat()
    r = client.get("/rail/trains", params={"from": "ndls", "to": "mmct", "date": day}, headers=h)
    assert r.status_code == 200, r.text
    t = r.json()["trains"][0]
    assert t["number"] == "12952" and t["name"] == "Mumbai Rajdhani"
    assert (t["departs"], t["arrives"], t["arrives_day_offset"]) == ("16:55", "08:35", 1)
    assert t["classes"] == ["1A", "2A", "3A"]
    client.get("/rail/trains", params={"from": "NDLS", "to": "MMCT", "date": day}, headers=h)
    assert len(calls) == 1  # second search came from the cache


def test_needs_login_and_sane_input(client):
    assert client.get("/rail/stations", params={"q": "delhi"}).status_code == 401
    h = signup(client)["headers"]
    r = client.get("/rail/trains", params={"from": "NDLS", "to": "NDLS", "date": date.today().isoformat()}, headers=h)
    assert r.status_code in (422, 503)
