"""Profile fields on users: date of birth, home town, phone, gender, interests.

Revision ID: 0009
Revises: 0008
Create Date: 2026-09-29
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


COLUMNS = (
    ("date_of_birth", sa.Date()),
    ("home_town", sa.String(120)),
    ("phone", sa.String(20)),
    ("gender", sa.String(20)),
    ("travel_interests", sa.JSON()),
)


def upgrade() -> None:
    # Idempotent: skips any column that is already there (e.g. from an
    # interrupted earlier attempt), so the migration can always be re-run.
    existing = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("users")}
    missing = [(n, t) for n, t in COLUMNS if n not in existing]
    if not missing:
        return
    with op.batch_alter_table("users") as batch:
        for name, type_ in missing:
            batch.add_column(sa.Column(name, type_, nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("users") as batch:
        for col in ("travel_interests", "gender", "phone", "home_town", "date_of_birth"):
            batch.drop_column(col)
