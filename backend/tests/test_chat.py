"""Support chat: understands the question, answers from the user's own data,
escalates when it should (once), and stays inside its limits."""
from datetime import date, datetime, timedelta, timezone

import pytest
from starlette.websockets import WebSocketDisconnect

from app.chat.classify import classify
from app.models.chat import ChatMessage, SupportEscalation
from app.models.trip import Trip
from app.notify.email import OUTBOX


def support_mails(at_least: int = 1, timeout: float = 3.0) -> int:
    """The alert is sent after the reply, in the server's thread pool -- so it
    can land a moment after the test has its answer. Wait for it."""
    import time

    deadline = time.monotonic() + timeout
    while True:
        n = sum(e.subject.startswith("[Support]") for e in OUTBOX)
        if n >= at_least or time.monotonic() > deadline:
            return n
        time.sleep(0.02)
from tests.helpers import OTHER, SIGNUP, create_trip, signup

TRIP = {
    "destination": "Jaipur", "start_date": (date.today() + timedelta(days=20)).isoformat(),
    "end_date": (date.today() + timedelta(days=22)).isoformat(),
    "budget": "30000", "travelers": 2, "style_tags": ["culture"], "use_memory": False,
}


def open_chat(client, token):
    ws = client.websocket_connect("/ws/chat")
    conn = ws.__enter__()
    conn.send_json({"type": "auth", "token": token})
    first = conn.receive_json()
    assert first["type"] == "history"
    return ws, conn, first["messages"]


def ask(conn, text):
    conn.send_json({"type": "message", "text": text})
    event = conn.receive_json()
    if event["type"] == "error":
        return event
    assert event["type"] == "typing"
    return conn.receive_json()


# --- classification ----------------------------------------------------------------

@pytest.mark.parametrize("text, intent, sentiment", [
    ("hi", "greeting", "neutral"),
    ("Where is my Goa itinerary?", "status_check", "neutral"),
    ("trip kab ready hoga", "status_check", "neutral"),
    ("I want to cancel my Jaipur trip", "cancel_trip", "neutral"),
    ("didn't get the verification email", "email_help", "neutral"),
    ("how do I download the pdf", "export_help", "neutral"),
    ("thanks, that was helpful", "thanks", "positive"),
    ("THIS APP IS USELESS, STILL NOT WORKING!!!", "other", "negative"),
    ("bakwas app hai", "other", "negative"),
    ("this is fine", "other", "neutral"),  # 'hi' inside 'this' must not count
])
def test_classifier(text, intent, sentiment):
    assert classify(text) == (intent, sentiment)


# --- answers grounded in the user's own data ---------------------------------------------

def test_history_is_empty_then_remembers_the_conversation(client):
    me = signup(client)
    ws, conn, history = open_chat(client, me["token"])
    assert history == []
    ask(conn, "hi")
    ws.__exit__(None, None, None)

    ws, conn, history = open_chat(client, me["token"])
    assert [m["sender"] for m in history] == ["user", "bot"]
    ws.__exit__(None, None, None)


def test_status_question_is_answered_from_their_latest_trip(client):
    me = signup(client)
    create_trip(client, TRIP, me["headers"])
    ws, conn, _ = open_chat(client, me["token"])
    reply = ask(conn, "is my itinerary ready?")["message"]["message"]
    ws.__exit__(None, None, None)
    assert "Jaipur" in reply and "ready" in reply


def test_a_stuck_trip_is_raised_even_when_asked_about_something_else(client, db_session, monkeypatch):
    from app.routers import trips as trips_router

    monkeypatch.setattr(trips_router, "enqueue", lambda *a, **k: None)
    me = signup(client)
    trip_id = client.post("/trips", json=TRIP, headers=me["headers"]).json()["id"]
    trip = db_session.get(Trip, __import__("uuid").UUID(trip_id))
    trip.created_at = datetime.now(timezone.utc) - timedelta(minutes=20)
    db_session.commit()

    ws, conn, _ = open_chat(client, me["token"])
    reply = ask(conn, "how do I download the pdf")["message"]["message"]
    ws.__exit__(None, None, None)
    assert "stuck" in reply and "Jaipur" in reply


def test_unverified_email_question_names_their_address(client):
    me = signup(client)
    ws, conn, _ = open_chat(client, me["token"])
    reply = ask(conn, "didn't get the verification email")["message"]["message"]
    ws.__exit__(None, None, None)
    assert SIGNUP["email"] in reply and "Resend email" in reply


def test_the_bot_never_claims_to_have_cancelled_anything(client):
    me = signup(client)
    create_trip(client, TRIP, me["headers"])
    ws, conn, _ = open_chat(client, me["token"])
    reply = ask(conn, "cancel my Jaipur trip")["message"]["message"]
    ws.__exit__(None, None, None)
    assert "Delete" in reply and "can't delete trips for you" in reply


def test_chats_never_cross_users(client):
    me = signup(client)
    ws, conn, _ = open_chat(client, me["token"])
    ask(conn, "hi")
    ws.__exit__(None, None, None)

    them = signup(client, OTHER)
    ws, conn, history = open_chat(client, them["token"])
    ws.__exit__(None, None, None)
    assert history == []
    assert client.get("/chat/history", headers=them["headers"]).json() == []


# --- escalation ---------------------------------------------------------------------

def test_an_upset_customer_is_handed_to_a_person_and_the_team_is_emailed(client, db_session):
    me = signup(client)
    OUTBOX.clear()
    ws, conn, _ = open_chat(client, me["token"])
    event = ask(conn, "This is useless, nothing works!!!")
    ws.__exit__(None, None, None)

    assert event["escalated"] is True
    reply = event["message"]["message"]
    assert reply.startswith("Sorry about the trouble.") and "support team" in reply
    assert "I can help with" not in reply, "no feature menu when handing to a person"
    [esc] = db_session.query(SupportEscalation).all()
    assert (esc.reason, esc.status) == ("negative_sentiment", "open")
    assert support_mails() >= 1


def test_the_same_question_three_times_escalates(client, db_session):
    me = signup(client)
    ws, conn, _ = open_chat(client, me["token"])
    first = ask(conn, "where is my trip?")
    second = ask(conn, "where is my trip??")
    third = ask(conn, "where is my trip")
    ws.__exit__(None, None, None)

    assert (first["escalated"], second["escalated"], third["escalated"]) == (False, False, True)
    assert db_session.query(SupportEscalation).one().reason == "repeated_issue"


def test_one_open_escalation_at_a_time(client, db_session):
    me = signup(client)
    OUTBOX.clear()
    ws, conn, _ = open_chat(client, me["token"])
    ask(conn, "this is useless")
    again = ask(conn, "still not working, worst app")
    ws.__exit__(None, None, None)

    assert again["escalated"] is True
    assert "already has your conversation" in again["message"]["message"]
    assert db_session.query(SupportEscalation).count() == 1
    assert support_mails() == 1, "the team is emailed once"


def test_greetings_and_thanks_never_escalate_however_often(client, db_session):
    me = signup(client)
    ws, conn, _ = open_chat(client, me["token"])
    for _ in range(4):
        ask(conn, "hi")
    ws.__exit__(None, None, None)
    assert db_session.query(SupportEscalation).count() == 0


# --- limits and auth ---------------------------------------------------------------

def test_messages_are_rate_limited_per_user(client, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "CHAT_MESSAGES_PER_MINUTE", 3)
    me = signup(client)
    ws, conn, _ = open_chat(client, me["token"])
    results = [ask(conn, "hi")["type"] for _ in range(4)]
    ws.__exit__(None, None, None)
    assert results == ["reply", "reply", "reply", "error"]


def test_overlong_and_empty_messages_are_refused_without_being_stored(client, db_session):
    me = signup(client)
    ws, conn, _ = open_chat(client, me["token"])
    assert ask(conn, "x" * 1001)["code"] == "too_long"
    assert ask(conn, "   ")["code"] == "empty"
    ws.__exit__(None, None, None)
    assert db_session.query(ChatMessage).count() == 0


def test_chat_needs_a_valid_token(client):
    with client.websocket_connect("/ws/chat") as ws:
        ws.send_json({"type": "auth", "token": "nope"})
        with pytest.raises(WebSocketDisconnect) as info:
            ws.receive_json()
        assert info.value.code == 4401


def test_escalation_alert_has_a_celery_task():
    from app.tasks import jobs
    from app.tasks.celery_app import task_for

    assert task_for(jobs.send_escalation_alert).name == "jobs.send_escalation_alert"
