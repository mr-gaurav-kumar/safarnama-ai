"""Instant place suggestions and sights for the plan editor."""


def names(client, q):
    return [r["name"] for r in client.get("/geo/suggest", params={"q": q}).json()]


def test_prefix_finds_the_destination(client):
    assert names(client, "Naini")[0] == "Nainital"
    assert names(client, "Jai")[:2] == ["Jaipur", "Jaisalmer"]


def test_typos_are_forgiven(client):
    assert names(client, "nanital")[0] == "Nainital"
    assert names(client, "manli")[0] == "Manali"


def test_aliases_and_cities(client):
    assert names(client, "bombay")[0] == "Mumbai"
    r = client.get("/geo/suggest", params={"q": "Noida"}).json()
    assert r and r[0]["kind"] == "city" and r[0]["lat"] is None


def test_attractions_follow_the_destination(client):
    sights = client.get("/geo/attractions", params={"destination": "Manali, Himachal Pradesh"}).json()
    assert "Hadimba Temple" in sights
    assert client.get("/geo/attractions", params={"destination": "Noida"}).json() == []
