"""My tickets: bookings made anywhere, saved and shown to their owner only."""
from app.core.config import settings
from tests.helpers import OTHER, create_trip, signup

PDF = b"%PDF-1.4\n" + b"t" * 400
TRIP = {"destination": "Manali", "start_date": "2026-12-20", "end_date": "2026-12-24", "budget": "40000",
        "travelers": 2, "style_tags": [], "use_memory": False}


def _add(client, h, **form):
    files = form.pop("files", None)
    return client.post("/me/tickets", data=form, files=files, headers=h)


def test_train_ticket_with_pnr_and_eticket(client):
    h = signup(client)["headers"]
    r = _add(client, h, mode="train", provider="Rajdhani Express", number="12951", pnr="4512 345 678",
             from_place="New Delhi (NDLS)", to_place="Mumbai Central (MMCT)", depart_at="2026-12-20T16:55",
             arrive_at="2026-12-21T08:35", seat="B3 / 45 LB", travel_class="3A", passengers="2", fare="5230",
             files={"file": ("eticket.pdf", PDF, "application/pdf")})
    assert r.status_code == 201, r.text
    t = r.json()
    assert t["pnr"] == "4512345678" and t["number"] == "12951" and t["passengers"] == 2 and t["has_file"]

    # The e-ticket is stored encrypted, not as a PDF.
    assert all(not f.read_bytes().startswith(b"%PDF") for f in settings.PRIVATE_DOCS_DIR.glob("*.bin"))
    assert client.get(f"/me/tickets/{t['id']}/file", headers=h).content == PDF

    # Without a RAPIDAPI_KEY, PNR status points to the official page.
    s = client.post(f"/me/tickets/{t['id']}/pnr-status", headers=h).json()
    assert s["live"] is False and s["enquiry_url"].startswith("https://www.indianrail.gov.in")


def test_formats_are_checked_per_mode(client):
    h = signup(client)["headers"]
    assert "10 digits" in _add(client, h, mode="train", pnr="12345").json()["detail"]
    assert "5 digits" in _add(client, h, mode="train", number="1295", pnr="4512345678").json()["detail"]
    assert "6E 2134" in _add(client, h, mode="flight", number="flight", pnr="X7K2QA").json()["detail"]
    assert _add(client, h, mode="flight", provider="IndiGo", number="6E 2134", pnr="x7k2qa").json()["pnr"] == "X7K2QA"
    assert _add(client, h, mode="bus", provider="zingbus", pnr="ZB-99812", seat="L4").status_code == 201
    assert _add(client, h, mode="hotel", provider="Snow Valley Resorts", depart_at="2026-12-20T12:00",
                arrive_at="2026-12-24T11:00").status_code == 201
    bad_times = _add(client, h, mode="bus", provider="X", depart_at="2026-12-20T12:00", arrive_at="2026-12-19T12:00")
    assert bad_times.status_code == 422
    assert _add(client, h, mode="other").status_code == 422  # nothing at all


def test_listed_soonest_first_and_linked_to_a_trip(client):
    h = signup(client)["headers"]
    trip = create_trip(client, TRIP, h)
    later = _add(client, h, mode="bus", provider="HRTC", depart_at="2026-12-24T18:00").json()
    sooner = _add(client, h, mode="flight", provider="IndiGo", number="6E 2134", depart_at="2026-12-20T06:00",
                  trip_id=trip["id"]).json()
    items = client.get("/me/tickets", headers=h).json()["items"]
    assert [i["id"] for i in items] == [sooner["id"], later["id"]]
    assert sooner["trip_destination"] == "Manali"
    on_trip = client.get(f"/me/tickets?trip_id={trip['id']}", headers=h).json()["items"]
    assert [i["id"] for i in on_trip] == [sooner["id"]]

    # Unlink, and edit keeps the kind of ticket.
    r = client.put(f"/me/tickets/{sooner['id']}", data={"mode": "train", "trip_id": "none", "seat": "12A"}, headers=h)
    assert r.json()["trip_id"] is None and r.json()["mode"] == "flight" and r.json()["seat"] == "12A"


def test_private_to_the_owner(client):
    garv = signup(client)["headers"]
    t = _add(client, garv, mode="train", pnr="4512345678", files={"file": ("e.pdf", PDF, "application/pdf")}).json()
    riya = signup(client, OTHER)["headers"]
    assert client.get("/me/tickets", headers=riya).json()["items"] == []
    for method, url in (("get", f"/me/tickets/{t['id']}/file"), ("delete", f"/me/tickets/{t['id']}"),
                        ("post", f"/me/tickets/{t['id']}/pnr-status")):
        assert getattr(client, method)(url, headers=riya).status_code == 404
    # Riya can't hang her ticket on Garv's trip either.
    trip = create_trip(client, TRIP, garv)
    assert _add(client, riya, mode="bus", provider="X", trip_id=trip["id"]).status_code == 422


def test_delete_removes_the_file(client):
    h = signup(client)["headers"]
    t = _add(client, h, mode="flight", provider="Air India", files={"file": ("e.pdf", PDF, "application/pdf")}).json()
    before = len(list(settings.PRIVATE_DOCS_DIR.glob("*.bin")))
    assert client.delete(f"/me/tickets/{t['id']}", headers=h).status_code == 204
    assert len(list(settings.PRIVATE_DOCS_DIR.glob("*.bin"))) == before - 1


def test_pnr_status_reads_the_live_answer(client, monkeypatch):
    from app.rail import irctc
    h = signup(client)["headers"]
    t = _add(client, h, mode="train", pnr="4512345678").json()
    monkeypatch.setattr(settings, "RAPIDAPI_KEY", "test")
    monkeypatch.setattr(irctc, "_get", lambda path, params: {"data": {
        "PassengerStatus": [{"BookingStatusNew": "WL 12", "CurrentStatusNew": "CNF B3 45"},
                            {"BookingStatusNew": "CNF B3 46", "CurrentStatusNew": "CNF B3 46"}],
        "ChartPrepared": True}})
    s = client.post(f"/me/tickets/{t['id']}/pnr-status", headers=h).json()
    assert s["live"] and s["status"] == "WL 12 → CNF B3 45, CNF B3 46 (chart prepared)"
    assert client.get("/me/tickets", headers=h).json()["items"][0]["status"] == s["status"]
