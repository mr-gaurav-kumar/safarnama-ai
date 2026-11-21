"""Shared test helpers."""

SIGNUP = {"name": "Garv", "email": "garv@example.com", "password": "a-good-password1"}
OTHER = {"name": "Riya", "email": "riya@example.com", "password": "another-password2"}


def signup(client, creds=SIGNUP) -> dict:
    """Returns {"headers": ..., "user": ...}."""
    body = client.post("/auth/signup", json=creds).json()
    return {"headers": {"Authorization": f"Bearer {body['access_token']}"}, "user": body["user"],
            "token": body["access_token"]}


def auth(client, creds=SIGNUP) -> dict:
    return signup(client, creds)["headers"]


def create_trip(client, payload, headers) -> dict:
    """POST /trips returns 202 with status 'processing'; the inline job has run
    by the time TestClient returns, so fetch the finished trip."""
    r = client.post("/trips", json=payload, headers=headers)
    assert r.status_code == 202, r.text
    assert r.json()["status"] == "processing"
    return client.get(f"/trips/{r.json()['id']}", headers=headers).json()


THIRD = {"name": "Aman", "email": "aman@example.com", "password": "third-password3"}


def verified(client, creds=SIGNUP) -> dict:
    """Sign up and confirm the email through the printed link."""
    from app.notify.email import OUTBOX

    me = signup(client, creds)
    link = [e for e in OUTBOX if e.to == creds["email"] and "/verify?token=" in e.text][-1]
    token = link.text.split("/verify?token=", 1)[1].split()[0]
    assert client.post("/auth/verify", json={"token": token}).status_code == 200
    return me


def invite_token(to_email: str) -> str:
    from app.notify.email import OUTBOX

    mail = [e for e in OUTBOX if e.to == to_email and "&token=" in e.text][-1]
    return mail.text.split("&token=", 1)[1].split()[0]
