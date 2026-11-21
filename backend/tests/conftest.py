"""Test fixtures.

The suite runs against in-memory SQLite, so it needs no Postgres, no Redis and
no network. Background jobs run inline -- Starlette's TestClient waits for them
to finish before returning -- so a test sees the finished trip right after
creating it.
"""
import os

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-not-used-anywhere-real")
# Tests always use the inline backend and never the timer-driven scheduler,
# whatever the developer's .env says.
os.environ["TASK_BACKEND"] = "inline"
os.environ["SCHEDULER_ENABLED"] = "false"
os.environ["SMTP_HOST"] = ""
os.environ["GEMINI_API_KEY"] = ""
# Never call the real geocoder from tests; test_geocoding.py turns it on with a
# fake HTTP layer.
os.environ["GEOCODING_ENABLED"] = "false"
os.environ["LIVE_WEATHER_ENABLED"] = "false"
# A throwaway vault key and folder for the tests -- never the real ones.
import tempfile as _tempfile  # noqa: E402

os.environ["DOCUMENT_ENCRYPTION_KEY"] = "dGVzdC1rZXktdGVzdC1rZXktdGVzdC1rZXktdGVzdC0="
os.environ["PRIVATE_DOCS_DIR"] = _tempfile.mkdtemp(prefix="vault-test-")
# TestClient calls the API directly (no Vite /api prefix), so the cookie must be
# scoped to /auth for its cookie jar to send it back.
os.environ["REFRESH_COOKIE_PATH"] = "/auth"
# Every test signs up several users from one "IP"; rate limits get their own tests.
os.environ["RATE_LIMIT_ENABLED"] = "false"
# In tests the designated admin is the first helper account (garv@example.com).
os.environ["ADMIN_EMAIL"] = "garv@example.com"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core import cache, database
from app.core.database import get_db
from app.main import app
from app.models import Base
from app.notify.email import OUTBOX
from app.realtime import progress


@pytest.fixture
def session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    yield factory
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db_session(session_factory):
    """A session for the test itself to inspect or change rows."""
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(session_factory, monkeypatch):
    def _get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _get_db
    # Background jobs and the WebSocket open sessions themselves.
    monkeypatch.setattr(database, "SessionLocal", session_factory)
    # Fresh broker, cache and empty outbox for every test.
    monkeypatch.setattr(progress, "_broker", progress.LocalBroker())
    monkeypatch.setattr(cache, "_cache", cache.MemoryCache())
    OUTBOX.clear()

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
