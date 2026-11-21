"""Phase 8: destination features for the recommender, and the planner's
"thinking" stored with each itinerary.

Revision ID: 0013
Revises: 0012
Create Date: 2026-10-08
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0013"
down_revision: Union[str, None] = "0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

JSONColumn = sa.JSON().with_variant(postgresql.JSONB, "postgresql")


def upgrade() -> None:
    op.create_table(
        "destination_features",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("state", sa.String(80), nullable=False),
        sa.Column("region", sa.String(40), nullable=False),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lng", sa.Float(), nullable=False),
        sa.Column("altitude_m", sa.Integer(), nullable=False),
        sa.Column("coastal", sa.Boolean(), nullable=False),
        sa.Column("daily_cost", sa.Integer(), nullable=False),
        sa.Column("styles", JSONColumn, nullable=False),
        sa.Column("blurb", sa.String(200), nullable=False, server_default=""),
        sa.Column("aliases", JSONColumn, nullable=False, server_default="[]"),
        sa.Column("closed_months", JSONColumn, nullable=False, server_default="[]"),
        sa.Column("source", sa.String(40), nullable=False, server_default="curated"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_destination_features_name", "destination_features", ["name"], unique=True)
    op.create_index("ix_destination_features_state", "destination_features", ["state"])
    op.add_column("itineraries", sa.Column("thinking", JSONColumn, nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("itineraries") as batch:
        batch.drop_column("thinking")
    op.drop_index("ix_destination_features_state", table_name="destination_features")
    op.drop_index("ix_destination_features_name", table_name="destination_features")
    op.drop_table("destination_features")
