"""PDF download and "email me this itinerary"."""
from app.notify.email import OUTBOX
from tests.helpers import OTHER, SIGNUP, auth, create_trip, signup

TRIP = {
    "destination": "Jaipur", "start_date": "2026-11-05", "end_date": "2026-11-07",
    "budget": "30000", "travelers": 2, "style_tags": ["culture"], "use_memory": False,
}


def verified(client, creds=SIGNUP):
    me = signup(client, creds)
    token = OUTBOX[-1].text.split("/verify?token=", 1)[1].split()[0]
    client.post("/auth/verify", json={"token": token})
    return me


def test_pdf_downloads_as_a_real_pdf(client):
    h = auth(client)
    trip = create_trip(client, TRIP, h)
    r = client.get(f"/trips/{trip['id']}/pdf", headers=h)
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert 'filename="jaipur-2026-11-05.pdf"' in r.headers["content-disposition"]
    assert r.content.startswith(b"%PDF") and len(r.content) > 1000


def test_pdf_survives_characters_its_fonts_cannot_draw(client, monkeypatch):
    """Model output can contain anything: rupee signs, Devanagari, emoji."""
    from app.services import trip_service
    from app.llm.itinerary import GeneratedItinerary

    def weird(**_):
        return GeneratedItinerary(
            day_plan=[{"day": 1, "date": "2026-11-05", "items": [
                {"time": "09:00", "place": "हवा महल — Hawa Mahal", "activity": "Sunrise “photo” walk 🌅",
                 "estimated_cost": 500}]}],
            budget_breakdown={"stay": 1000, "food": 500, "travel": 300, "misc": 200},
            explanation="Budget ₹2,000 – café hopping…",
        )

    monkeypatch.setattr(trip_service, "generate_itinerary", weird)
    h = auth(client)
    trip = create_trip(client, {**TRIP, "end_date": "2026-11-05"}, h)
    r = client.get(f"/trips/{trip['id']}/pdf", headers=h)
    assert r.status_code == 200 and r.content.startswith(b"%PDF")


def test_someone_elses_pdf_is_not_found(client):
    trip = create_trip(client, TRIP, auth(client))
    assert client.get(f"/trips/{trip['id']}/pdf", headers=auth(client, OTHER)).status_code == 404


def test_pdf_of_an_unfinished_trip_is_refused(client, monkeypatch):
    from app.routers import trips as trips_router

    monkeypatch.setattr(trips_router, "enqueue", lambda *a, **k: None)
    h = auth(client)
    trip_id = client.post("/trips", json=TRIP, headers=h).json()["id"]
    assert client.get(f"/trips/{trip_id}/pdf", headers=h).status_code == 409


def test_email_sends_the_pdf_to_a_verified_user(client):
    me = verified(client)
    trip = create_trip(client, TRIP, me["headers"])
    OUTBOX.clear()

    r = client.post(f"/trips/{trip['id']}/email", headers=me["headers"])
    assert r.status_code == 202
    [email] = list(OUTBOX)
    assert email.to == SIGNUP["email"]
    [pdf] = email.attachments
    assert pdf.filename == "jaipur-2026-11-05.pdf"
    assert pdf.content.startswith(b"%PDF")


def test_email_is_refused_until_the_address_is_verified(client):
    h = auth(client)
    trip = create_trip(client, TRIP, h)
    OUTBOX.clear()
    r = client.post(f"/trips/{trip['id']}/email", headers=h)
    assert r.status_code == 403
    assert list(OUTBOX) == []


def test_email_job_has_a_celery_task():
    from app.tasks import jobs
    from app.tasks.celery_app import task_for

    assert task_for(jobs.send_itinerary_copy_email).name == "jobs.send_itinerary_copy_email"
