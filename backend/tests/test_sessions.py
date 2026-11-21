"""Staying logged in: refresh cookies, rotation, reuse detection, logout."""
from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.models.refresh_token import RefreshToken
from app.models.user import User
from tests.helpers import SIGNUP, signup

HDR = {"X-Requested-With": "fetch"}
NAME = "tp_refresh"


def present(client, cookie):
    """Make `cookie` the only refresh cookie the client holds -- as a browser
    (or a thief's browser) holding exactly that token would."""
    client.cookies.clear()
    client.cookies.set(NAME, cookie, domain="testserver.local", path="/auth")


def refresh(client, cookie=None):
    if cookie is not None:
        present(client, cookie)
    return client.post("/auth/refresh", headers=HDR)


# --- the cookie ------------------------------------------------------------------

def test_login_sets_an_httponly_strict_cookie_scoped_to_auth(client):
    signup(client)
    r = client.post("/auth/login", json={"email": SIGNUP["email"], "password": SIGNUP["password"]})
    cookie = r.headers["set-cookie"]
    assert cookie.startswith(f"{NAME}=")
    assert "HttpOnly" in cookie and "SameSite=strict" in cookie and "Path=/auth" in cookie


def test_the_database_holds_only_a_hash(client, db_session):
    signup(client)
    raw = client.cookies.get(NAME)
    [row] = db_session.query(RefreshToken).all()
    assert raw and row.token_hash != raw and len(row.token_hash) == 64


# --- refreshing --------------------------------------------------------------

def test_refresh_restores_the_session_after_a_reload(client):
    """A reload loses the in-memory access token; the cookie brings it back."""
    signup(client)
    r = refresh(client)
    assert r.status_code == 200
    body = r.json()
    assert body["user"]["email"] == SIGNUP["email"]
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200


def test_every_refresh_rotates_the_cookie(client):
    signup(client)
    first = client.cookies.get(NAME)
    refresh(client)
    second = client.cookies.get(NAME)
    assert first != second


def test_no_cookie_means_no_session(client):
    assert client.post("/auth/refresh", headers=HDR).status_code == 401


def test_the_csrf_header_is_required(client):
    signup(client)
    assert client.post("/auth/refresh").status_code == 403


def test_two_tabs_refreshing_at_once_both_succeed(client):
    """Tab B presents the token tab A has just rotated -- a race, not theft."""
    signup(client)
    shared = client.cookies.get(NAME)
    assert refresh(client, shared).status_code == 200   # tab A
    assert refresh(client, shared).status_code == 200   # tab B, inside the grace


def test_an_old_token_after_the_grace_ends_the_whole_session(client, monkeypatch, db_session):
    """Reuse of a rotated token means a copy exists somewhere it should not.
    Revoke the family, so the thief's copy and the victim's current one both die."""
    monkeypatch.setattr(settings, "REFRESH_REUSE_GRACE_SECONDS", 0)
    signup(client)
    stolen = client.cookies.get(NAME)
    refresh(client)                                   # victim rotates
    current = client.cookies.get(NAME)

    assert refresh(client, stolen).status_code == 401  # thief replays
    assert refresh(client, current).status_code == 401, "the victim's session is ended too"
    reasons = {r.revoke_reason for r in db_session.query(RefreshToken).all()}
    assert "reuse" in reasons


def test_an_expired_refresh_token_is_refused(client, db_session):
    signup(client)
    row = db_session.query(RefreshToken).one()
    row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db_session.commit()
    assert refresh(client).status_code == 401


def test_a_blocked_user_cannot_refresh(client, db_session):
    signup(client)
    user = db_session.query(User).one()
    user.is_blocked = True
    db_session.commit()
    r = refresh(client)
    assert r.status_code == 403
    assert db_session.query(RefreshToken).filter(RefreshToken.revoked_at.is_(None)).count() == 0


def test_a_failed_refresh_clears_the_cookie(client):
    r = refresh(client, "not-a-real-token")
    assert r.status_code == 401
    assert f'{NAME}=""' in r.headers["set-cookie"] or "Max-Age=0" in r.headers["set-cookie"]


# --- logging out ---------------------------------------------------------------

def test_logout_ends_the_session(client):
    signup(client)
    token = client.cookies.get(NAME)
    assert client.post("/auth/logout").status_code == 204
    assert refresh(client, token).status_code == 401


def test_logout_without_a_session_still_succeeds(client):
    assert client.post("/auth/logout").status_code == 204


def test_logging_out_one_device_leaves_the_other_logged_in(client):
    signup(client)
    laptop = client.cookies.get(NAME)
    client.cookies.clear()
    client.post("/auth/login", json={"email": SIGNUP["email"], "password": SIGNUP["password"]})
    phone = client.cookies.get(NAME)

    present(client, laptop)
    client.post("/auth/logout")

    assert refresh(client, phone).status_code == 200
