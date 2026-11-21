"""Verification, which emails go to whom, and reminders."""
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.core.config import settings
from app.notify.email import OUTBOX, EmailDeliveryError
from tests.helpers import OTHER, SIGNUP, create_trip, signup


def token_from(email) -> str:
    return email.text.split("/verify?token=", 1)[1].split()[0]


def verify(client, creds=SIGNUP) -> dict:
    me = signup(client, creds)
    link = [e for e in OUTBOX if e.to == creds["email"]][-1]
    r = client.post("/auth/verify", json={"token": token_from(link)})
    assert r.status_code == 200, r.text
    return me


def trip_on(start: date, days: int = 3, name: str = "Goa") -> dict:
    return {
        "destination": name,
        "start_date": start.isoformat(),
        "end_date": (start + timedelta(days=days - 1)).isoformat(),
        "budget": "25000", "travelers": 2, "style_tags": ["relax"], "use_memory": False,
    }


def today() -> date:
    return datetime.now(ZoneInfo(settings.APP_TIMEZONE)).date()


# --- verification ---------------------------------------------------------------

def test_signup_sends_a_verification_link(client):
    signup(client)
    [email] = list(OUTBOX)
    assert email.to == SIGNUP["email"]
    assert "/verify?token=" in email.text


def test_the_link_verifies_the_account(client):
    me = verify(client)
    assert client.get("/auth/me", headers=me["headers"]).json()["is_verified"] is True


def test_a_verification_token_cannot_be_used_to_log_in(client):
    """The link in the email is a signed token with the user's id. If token
    types were not checked, anyone who saw that email could use it as a login."""
    signup(client)
    token = token_from(OUTBOX[-1])
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_an_access_token_cannot_verify_an_email(client):
    me = signup(client)
    assert client.post("/auth/verify", json={"token": me["token"]}).status_code == 400


def test_a_garbage_token_is_rejected(client):
    assert client.post("/auth/verify", json={"token": "nope"}).status_code == 400


def test_resend_sends_again_until_verified(client):
    me = signup(client)
    client.post("/auth/resend-verification", headers=me["headers"])
    assert len(OUTBOX) == 2

    client.post("/auth/verify", json={"token": token_from(OUTBOX[-1])})
    client.post("/auth/resend-verification", headers=me["headers"])
    assert len(OUTBOX) == 2, "no more links once verified"


# --- itinerary-ready emails -------------------------------------------------------

def test_no_trip_emails_to_an_unconfirmed_address(client):
    """Otherwise anyone could type a stranger's address at sign-up and have
    this app mail them."""
    me = signup(client)
    OUTBOX.clear()
    create_trip(client, trip_on(today() + timedelta(days=30)), me["headers"])
    assert list(OUTBOX) == []


def test_a_verified_user_is_told_when_the_plan_is_ready(client):
    me = verify(client)
    OUTBOX.clear()
    trip = create_trip(client, trip_on(today() + timedelta(days=30)), me["headers"])
    [email] = list(OUTBOX)
    assert email.subject == "Your Goa itinerary is ready"
    assert f"/trips/{trip['id']}" in email.text


# --- reminders ------------------------------------------------------------------

def reminders():
    from app.tasks.jobs import send_trip_reminders
    return send_trip_reminders()


def test_a_trip_starting_soon_gets_one_reminder(client):
    me = verify(client)
    create_trip(client, trip_on(today() + timedelta(days=1)), me["headers"])
    OUTBOX.clear()

    assert reminders() == 1
    assert OUTBOX[-1].subject == "Your Goa trip starts tomorrow"
    assert reminders() == 0, "never twice, however often the job runs"


def test_trips_outside_the_window_are_left_alone(client):
    me = verify(client)
    create_trip(client, trip_on(today() + timedelta(days=10)), me["headers"], )
    create_trip(client, trip_on(today() - timedelta(days=5), name="Jaipur"), me["headers"])
    OUTBOX.clear()
    assert reminders() == 0


def test_unverified_users_get_no_reminder(client):
    me = signup(client, OTHER)
    create_trip(client, trip_on(today() + timedelta(days=1)), me["headers"])
    OUTBOX.clear()
    assert reminders() == 0


def test_a_failed_send_is_retried_next_run(client, monkeypatch):
    from app.tasks import jobs

    me = verify(client)
    create_trip(client, trip_on(today() + timedelta(days=2)), me["headers"])

    real_send = jobs.send_email

    def smtp_down(_email):
        raise EmailDeliveryError("smtp down")

    monkeypatch.setattr(jobs, "send_email", smtp_down)
    assert reminders() == 0

    # Restore only this patch -- monkeypatch.undo() would also undo the test
    # database the client fixture set up.
    monkeypatch.setattr(jobs, "send_email", real_send)
    OUTBOX.clear()
    assert reminders() == 1, "not marked sent, so it goes out once SMTP is back"
