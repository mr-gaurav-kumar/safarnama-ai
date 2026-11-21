SIGNUP = {"name": "Garv", "email": "garv@example.com", "password": "a-good-password1"}


def test_signup_creates_account_and_returns_a_usable_token(client):
    r = client.post("/auth/signup", json=SIGNUP)
    assert r.status_code == 201, r.text
    body = r.json()

    assert body["user"]["email"] == "garv@example.com"
    assert body["user"]["role"] == "user"
    assert "password" not in str(body), "no password field may appear in a response"

    me = client.get("/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert me.json()["email"] == "garv@example.com"


def test_signup_is_case_insensitive_on_email(client):
    client.post("/auth/signup", json=SIGNUP)
    r = client.post("/auth/signup", json={**SIGNUP, "email": "GARV@example.com"})
    assert r.status_code == 409


def test_login_succeeds_and_rejects_a_wrong_password(client):
    client.post("/auth/signup", json=SIGNUP)

    ok = client.post("/auth/login", json={"email": SIGNUP["email"], "password": SIGNUP["password"]})
    assert ok.status_code == 200

    bad = client.post("/auth/login", json={"email": SIGNUP["email"], "password": "not-it"})
    assert bad.status_code == 401


def test_unknown_email_and_wrong_password_are_indistinguishable(client):
    """Different messages here would let anyone test which emails are registered."""
    client.post("/auth/signup", json=SIGNUP)

    unknown = client.post("/auth/login", json={"email": "nobody@example.com", "password": "x" * 10})
    wrong = client.post("/auth/login", json={"email": SIGNUP["email"], "password": "x" * 10})

    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json()["detail"] == wrong.json()["detail"]


def test_blocked_user_cannot_log_in_or_use_an_existing_token(client, db_session):
    from app.models.user import User

    token = client.post("/auth/signup", json=SIGNUP).json()["access_token"]

    user = db_session.query(User).one()
    user.is_blocked = True
    db_session.commit()

    # An already-issued token must stop working immediately, not at expiry.
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 403

    login = client.post("/auth/login", json={"email": SIGNUP["email"], "password": SIGNUP["password"]})
    assert login.status_code == 403


def test_me_requires_a_token(client):
    assert client.get("/auth/me").status_code == 401
    assert client.get("/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_short_password_is_rejected_by_validation(client):
    r = client.post("/auth/signup", json={**SIGNUP, "password": "short"})
    assert r.status_code == 422
