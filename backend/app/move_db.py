"""Move everything from the current database (usually local SQLite) into a new
Postgres one, e.g. Supabase:

    1. put the new database's link in .env as SUPABASE_DATABASE_URL=...
    2. python -m app.cli move-to-postgres
    3. when it says done, swap DATABASE_URL in .env for that link and restart

What it does: creates every table in the target with the normal migrations
(which also switch on pgvector), then copies each table's rows in dependency
order. Nothing in the source is changed or deleted, so it is safe to re-run.
It refuses to copy into a database that already has users, so it never mixes
two copies. Uploaded files (documents, photos) stay where they are on disk.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, func, select, text

from app.core.config import BACKEND_DIR, PROJECT_ROOT, Settings, settings

BATCH = 500


def _target_url() -> str | None:
    """SUPABASE_DATABASE_URL from the environment or either .env file."""
    if os.environ.get("SUPABASE_DATABASE_URL"):
        raw = os.environ["SUPABASE_DATABASE_URL"]
    else:
        raw = None
        for env in (PROJECT_ROOT / ".env", BACKEND_DIR / ".env"):
            if not Path(env).exists():
                continue
            for line in Path(env).read_text(encoding="utf-8").splitlines():
                if line.strip().startswith("SUPABASE_DATABASE_URL="):
                    raw = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not raw:
        return None
    return Settings._db_driver(raw)  # same driver fix the app uses


def _hide(url: str) -> str:
    """The link without its password, for printing."""
    if "@" not in url or "://" not in url:
        return url
    scheme, rest = url.split("://", 1)
    creds, host = rest.rsplit("@", 1)
    return f"{scheme}://{creds.split(':', 1)[0]}:***@{host}"


def move_to_postgres(target: str | None = None, *, run_migrations: bool = True) -> int:
    from app.models import Base

    target = target or _target_url()
    if not target:
        print("Add SUPABASE_DATABASE_URL=<your Postgres link> to .env first.")
        return 2
    if "[YOUR-" in target:
        print("The link still has the [YOUR-...-PASSWORD] placeholder -- put your database password there (no brackets).")
        return 2
    source = settings.DATABASE_URL
    if source == target:
        print("DATABASE_URL already points at that database -- nothing to move.")
        return 1
    print(f"From: {_hide(source)}\nTo:   {_hide(target)}")

    dst = create_engine(target, pool_pre_ping=True)
    try:
        with dst.connect() as c:
            c.execute(text("select 1"))
    except Exception as exc:  # noqa: BLE001
        print(f"Could not connect to the new database: {str(exc).splitlines()[0]}")
        print("Check the password in the link, and that you copied the Session pooler link.")
        return 1

    if run_migrations:
        print("Creating tables (migrations)...", flush=True)
        env = {**os.environ, "DATABASE_URL": target}
        r = subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=BACKEND_DIR, env=env)
        if r.returncode != 0:
            print("Migrations failed -- see the error above. Nothing was copied.")
            return 1

    users = Base.metadata.tables["users"]
    with dst.connect() as c:
        if c.execute(select(func.count()).select_from(users)).scalar():
            print("The new database already has users in it. Not copying, so nothing is mixed or duplicated.")
            return 1

    src = create_engine(source)
    tables = Base.metadata.sorted_tables  # parents before children
    total = 0
    with src.connect() as s, dst.begin() as d:
        for table in reversed(tables):  # clear anything the migrations seeded
            d.execute(table.delete())
        for table in tables:
            rows = [dict(r._mapping) for r in s.execute(select(table))]
            for i in range(0, len(rows), BATCH):
                d.execute(table.insert(), rows[i:i + BATCH])
            total += len(rows)
            if rows:
                print(f"  {table.name:<28} {len(rows):>6}", flush=True)
    print(f"Done: {total} rows copied into the new database. Your old database is unchanged.")
    print("Next: in .env set DATABASE_URL to the same link as SUPABASE_DATABASE_URL, then restart the backend.")
    return 0
