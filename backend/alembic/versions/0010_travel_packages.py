"""Travel packages and bookings.

Revision ID: 0010
Revises: 0009
Create Date: 2026-09-30
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

JSONColumn = sa.JSON().with_variant(postgresql.JSONB, "postgresql")


def _ts() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    ]


def upgrade() -> None:
    op.create_table(
        "travel_packages",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("destination", sa.String(200), nullable=False),
        sa.Column("duration_days", sa.Integer(), nullable=False),
        sa.Column("price_per_person", sa.Numeric(12, 2), nullable=False),
        sa.Column("summary", sa.String(300), nullable=False, server_default=""),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("inclusions", JSONColumn, nullable=False),
        sa.Column("highlights", JSONColumn, nullable=False),
        sa.Column("style_tags", JSONColumn, nullable=False),
        sa.Column("seats", sa.Integer(), nullable=True),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_until", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        *_ts(),
    )
    op.create_table(
        "package_bookings",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("package_id", sa.Uuid(as_uuid=True), sa.ForeignKey("travel_packages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("travelers", sa.Integer(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("total_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("note", sa.String(500), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        *_ts(),
    )
    op.create_index("ix_package_bookings_package_id", "package_bookings", ["package_id"])
    op.create_index("ix_package_bookings_user_id", "package_bookings", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_package_bookings_user_id", table_name="package_bookings")
    op.drop_index("ix_package_bookings_package_id", table_name="package_bookings")
    op.drop_table("package_bookings")
    op.drop_table("travel_packages")
