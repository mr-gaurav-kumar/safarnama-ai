"""Create trips and itineraries.

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-18
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Matches app.models.trip.JSONColumn -- JSONB on Postgres, JSON elsewhere.
JSONColumn = sa.JSON().with_variant(postgresql.JSONB, "postgresql")


def upgrade() -> None:
    op.create_table(
        "trips",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.Uuid(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("destination", sa.String(200), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("budget", sa.Numeric(12, 2), nullable=False),
        sa.Column("travelers", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("style_tags", JSONColumn, nullable=False),
        sa.Column("use_memory", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("status", sa.String(20), nullable=False, server_default="processing"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("plan_status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index("ix_trips_user_id", "trips", ["user_id"])

    op.create_table(
        "itineraries",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("trip_id", sa.Uuid(as_uuid=True),
                  sa.ForeignKey("trips.id", ondelete="CASCADE"),
                  nullable=False, unique=True),
        sa.Column("day_plan", JSONColumn, nullable=False),
        sa.Column("budget_breakdown", JSONColumn, nullable=False),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index("ix_itineraries_trip_id", "itineraries", ["trip_id"])


def downgrade() -> None:
    op.drop_index("ix_itineraries_trip_id", table_name="itineraries")
    op.drop_table("itineraries")
    op.drop_index("ix_trips_user_id", table_name="trips")
    op.drop_table("trips")
