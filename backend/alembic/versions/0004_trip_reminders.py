"""Track when each trip's reminder email was sent.

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-23
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("trips") as batch:
        batch.add_column(
            sa.Column("reminder_sent_at", sa.DateTime(timezone=True), nullable=True)
        )
    # The reminder job filters on start date every day.
    op.create_index("ix_trips_start_date", "trips", ["start_date"])


def downgrade() -> None:
    op.drop_index("ix_trips_start_date", table_name="trips")
    with op.batch_alter_table("trips") as batch:
        batch.drop_column("reminder_sent_at")
