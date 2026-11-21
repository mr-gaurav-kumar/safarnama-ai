"""Indian city suggestions for sign-up and profile."""


def test_prefix_suggestions_come_with_their_state(client, monkeypatch):
    from app.routers import geo
    monkeypatch.setattr(geo, "search_indian_places", lambda q, n: [])
    r = client.get("/geo/cities", params={"q": "gha"})
    assert r.status_code == 200
    labels = [x["label"] for x in r.json()]
    assert "Ghaziabad, Uttar Pradesh" in labels

    jai = client.get("/geo/cities", params={"q": "jai"}).json()
    assert jai[0]["label"] == "Jaipur, Rajasthan"

    leh = client.get("/geo/cities", params={"q": "leh"}).json()
    assert {"name": "Leh", "state": "Ladakh", "label": "Leh, Ladakh"} in leh


def test_rare_town_falls_back_to_map_search(client, monkeypatch):
    from app.routers import geo
    monkeypatch.setattr(geo, "search_indian_places", lambda q, n: [{"name": "Zzyzx", "state": "Goa", "label": "Zzyzx, Goa"}])
    r = client.get("/geo/cities", params={"q": "zzyzx"}).json()
    assert r == [{"name": "Zzyzx", "state": "Goa", "label": "Zzyzx, Goa"}]
