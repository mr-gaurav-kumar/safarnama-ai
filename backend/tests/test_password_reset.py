"""Forgotten password: reset link by email, single use, signs out everywhere."""
from app.notify.email import OUTBOX
from tests.helpers import SIGNUP, signup

NEW = "a-brand-new-pass9"


def reset_token(to: str) -> str:
    mail = [e for e in OUTBOX if e.to == to and "/reset-password?token=" in e.text][-1]
    return mail.text.split("/reset-password?token=", 1)[1].split()[0]


def test_same_reply_for_known_and_unknown_emails(client):
    signup(client)
    known = client.post("/auth/forgot-password", json={"email": SIGNUP["email"]})
    unknown = client.post("/auth/forgot-password", json={"email": "nobody@example.com"})
    assert known.status_code == unknown.status_code == 202
    assert known.json() == unknown.json()
    assert not [e for e in OUTBOX if e.to == "nobody@example.com"]


def test_reset_link_changes_the_password(client):
    signup(client)
    client.post("/auth/forgot-password", json={"email": SIGNUP["email"].upper()})
    r = client.post("/auth/reset-password", json={"token": reset_token(SIGNUP["email"]), "password": NEW})
    assert r.status_code == 200, r.text

    old = client.post("/auth/login", json={"email": SIGNUP["email"], "password": SIGNUP["password"]})
    new = client.post("/auth/login", json={"email": SIGNUP["email"], "password": NEW})
    assert old.status_code == 401
    assert new.status_code == 200
    assert any("password was changed" in e.subject for e in OUTBOX)


def test_reset_link_works_only_once(client):
    signup(client)
    client.post("/auth/forgot-password", json={"email": SIGNUP["email"]})
    token = reset_token(SIGNUP["email"])
    assert client.post("/auth/reset-password", json={"token": token, "password": NEW}).status_code == 200
    again = client.post("/auth/reset-password", json={"token": token, "password": "another-one-77"})
    assert again.status_code == 400


def test_weak_password_and_bad_token_are_rejected(client):
    signup(client)
    client.post("/auth/forgot-password", json={"email": SIGNUP["email"]})
    token = reset_token(SIGNUP["email"])
    assert client.post("/auth/reset-password", json={"token": token, "password": "onlyletters"}).status_code == 422
    assert client.post("/auth/reset-password", json={"token": "x" * 40, "password": NEW}).status_code == 400
