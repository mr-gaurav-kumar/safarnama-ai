"""Sign in with Google. Google's token check is replaced with a fake here --
the tests are about what we do with a verified identity, and never touch
the network."""
import pytest

from app.core.config import settings
from app.services import google_auth
from tests.helpers import SIGNUP, signup, verified


@pytest.fixture
def google(monkeypatch):
    """`google(sub, email)` makes the next credential verify as that account."""
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "test-client.apps.googleusercontent.com")
    who = {}

    def fake_verify(credential: str):
        if credential != "good":
            raise google_auth.GoogleAuthError("Google sign-in failed. Please try again.")
        return google_auth.GoogleIdentity(**who)

    monkeypatch.setattr(google_auth, "verify", fake_verify)

    def set_identity(sub: str, email: str, name: str = "Google User"):
        who.update(sub=sub, email=email, name=name)
    return set_identity


def test_providers_hides_google_until_configured(client, monkeypatch):
    assert client.get("/auth/providers").json() == {"google_client_id": None}
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "abc.apps.googleusercontent.com")
    assert client.get("/auth/providers").json()["google_client_id"] == "abc.apps.googleusercontent.com"


def test_new_google_user_is_created_verified_and_comes_back_as_same_account(client, google):
    google("g-123", "neha@gmail.com", "Neha")
    r = client.post("/auth/google", json={"credential": "good"})
    assert r.status_code == 200, r.text
    user = r.json()["user"]
    assert user["email"] == "neha@gmail.com" and user["is_verified"] and user["role"] == "user"

    # Same Google account later, even if its email changed -> same user.
    google("g-123", "neha.new@gmail.com", "Neha")
    again = client.post("/auth/google", json={"credential": "good"}).json()["user"]
    assert again["id"] == user["id"]
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {r.json()['access_token']}"}).status_code == 200


def test_bad_token_is_rejected(client, google):
    google("g-1", "x@gmail.com")
    assert client.post("/auth/google", json={"credential": "forged"}).status_code == 401


def test_links_to_existing_verified_account_and_password_still_works(client, google):
    verified(client)  # garv@example.com, a verified password account
    google("g-garv", SIGNUP["email"])
    r = client.post("/auth/google", json={"credential": "good"})
    assert r.status_code == 200
    login = client.post("/auth/login", json={"email": SIGNUP["email"], "password": SIGNUP["password"]})
    assert login.status_code == 200 and login.json()["user"]["id"] == r.json()["user"]["id"]


def test_unverified_squatter_password_is_wiped_on_link(client, google):
    """Someone registers YOUR email with their password and never verifies it.
    When you sign in with Google, their password must stop working."""
    squatter = {"name": "Not You", "email": "victim@gmail.com", "password": "squatter-pass9"}
    signup(client, squatter)
    google("g-victim", "victim@gmail.com", "Victim")
    assert client.post("/auth/google", json={"credential": "good"}).status_code == 200
    r = client.post("/auth/login", json={"email": squatter["email"], "password": squatter["password"]})
    assert r.status_code == 401


def test_blocked_user_cannot_sign_in_with_google(client, google, session_factory):
    from app.models.user import User
    google("g-b", "blocked@gmail.com")
    client.post("/auth/google", json={"credential": "good"})
    with session_factory() as db:
        db.query(User).filter_by(email="blocked@gmail.com").update({"is_blocked": True})
        db.commit()
    assert client.post("/auth/google", json={"credential": "good"}).status_code == 403


def test_admin_email_via_google_becomes_admin(client, google):
    google("g-admin", SIGNUP["email"])  # ADMIN_EMAIL in the test settings
    r = client.post("/auth/google", json={"credential": "good"})
    assert r.json()["user"]["role"] == "admin"


def test_server_without_client_id_refuses(client):
    r = client.post("/auth/google", json={"credential": "anything"})
    assert r.status_code == 401
