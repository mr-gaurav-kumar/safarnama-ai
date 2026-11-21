"""SQLAlchemy engine, session factory and the FastAPI dependency."""
import sqlite3
from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

@event.listens_for(Engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, _record) -> None:
    """SQLite ignores foreign keys unless told otherwise, so ON DELETE CASCADE
    silently does nothing and deleting a trip leaves its embedding behind.
    Postgres always enforces them; this makes development behave the same."""
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,   # survives Postgres dropping an idle connection
    echo=False,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: one session per request, always closed."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
