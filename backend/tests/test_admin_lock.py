"""The one-admin rule: only the verified ADMIN_EMAIL account is ever an admin.

In tests ADMIN_EMAIL is garv@example.com (see conftest.py).
"""
from app.core.config import settings
from app.models.user import User
from tests.helpers import OTHER, SIGNUP, signup, verified


def role_of(db, email):
    db.expire_all()
    return db.query(User).filter(User.email == email).one().role


def test_the_owner_becomes_admin_by_verifying_no_command_needed(client, db_session):
    me = signup(client)
    assert role_of(db_session, SIGNUP["email"]) == "user", "not before the email is confirmed"
    assert client.get("/admin/stats", headers=me["headers"]).status_code == 403

    # Verify this same account through its emailed link.
    from app.notify.email import OUTBOX
    link = [e for e in OUTBOX if e.to == SIGNUP["email"]][-1]
    client.post("/auth/verify", json={"token": link.text.split("/verify?token=", 1)[1].split()[0]})
    assert role_of(db_session, SIGNUP["email"]) == "admin"
    assert client.get("/admin/stats", headers=me["headers"]).status_code == 200


def test_an_already_verified_owner_becomes_admin_at_next_login(client, db_session):
    verified(client)
    u = db_session.query(User).filter(User.email == SIGNUP["email"]).one()
    u.role = "user"  # e.g. an account verified before this rule existed
    db_session.commit()
    client.post("/auth/login", json={"email": SIGNUP["email"], "password": SIGNUP["password"]})
    assert role_of(db_session, SIGNUP["email"]) == "admin"


def test_anyone_else_with_the_admin_role_gets_nothing_and_loses_it(client, db_session):
    """A role set by hand in the database is not enough."""
    other = verified(client, OTHER)
    u = db_session.query(User).filter(User.email == OTHER["email"]).one()
    u.role = "admin"
    db_session.commit()

    assert client.get("/admin/stats", headers=other["headers"]).status_code == 403
    client.post("/auth/login", json={"email": OTHER["email"], "password": OTHER["password"]})
    assert role_of(db_session, OTHER["email"]) == "user"


def test_an_unverified_signup_with_the_owners_address_is_not_admin(client, db_session):
    """Someone who types the owner's Gmail at sign-up cannot read its inbox,
    so they can never verify -- and never become admin."""
    impostor = signup(client, {**SIGNUP, "name": "Impostor"})
    u = db_session.query(User).filter(User.email == SIGNUP["email"]).one()
    u.role = "admin"  # even if the role were somehow set
    db_session.commit()
    assert client.get("/admin/stats", headers=impostor["headers"]).status_code == 403


def test_a_business_account_keeps_its_role_at_login(client, db_session):
    from tests.test_business import BIZ

    client.post("/auth/signup-business", json=BIZ)
    client.post("/auth/login", json={"email": BIZ["email"], "password": BIZ["password"]})
    assert role_of(db_session, BIZ["email"]) == "business"


def test_cli_refuses_any_other_address(client, db_session, monkeypatch, capsys):
    from app import cli
    from app.core import database

    monkeypatch.setattr(cli, "SessionLocal", database.SessionLocal)
    signup(client, OTHER)
    assert cli.main(["make-admin", OTHER["email"]]) == 1
    assert "Only the address in ADMIN_EMAIL" in capsys.readouterr().out
    assert role_of(db_session, OTHER["email"]) == "user"


def test_no_admin_email_means_no_admin_at_all(client, db_session, monkeypatch):
    me = verified(client)
    monkeypatch.setattr(settings, "ADMIN_EMAIL", "")
    assert client.get("/admin/stats", headers=me["headers"]).status_code == 403
