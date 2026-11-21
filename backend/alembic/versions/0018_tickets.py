"""My tickets: bookings made anywhere, saved in one place.

Revision ID: 0018
Revises: 0017
Create Date: 2026-11-21
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0018"
down_revision: Union[str, None] = "0017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tickets",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("trip_id", sa.Uuid(as_uuid=True), sa.ForeignKey("trips.id", ondelete="SET NULL"), nullable=True),
        sa.Column("mode", sa.String(10), nullable=False),
        sa.Column("provider", sa.String(80), nullable=True),
        sa.Column("number", sa.String(30), nullable=True),
        sa.Column("pnr_enc", sa.Text(), nullable=True),
        sa.Column("from_place", sa.String(120), nullable=True),
        sa.Column("to_place", sa.String(120), nullable=True),
        sa.Column("depart_at", sa.DateTime(), nullable=True),
        sa.Column("arrive_at", sa.DateTime(), nullable=True),
        sa.Column("seat", sa.String(60), nullable=True),
        sa.Column("travel_class", sa.String(30), nullable=True),
        sa.Column("passengers", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("fare", sa.Numeric(12, 2), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(120), nullable=True),
        sa.Column("status_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("file_name", sa.String(80), nullable=True),
        sa.Column("file_type", sa.String(40), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_tickets_user_id", "tickets", ["user_id"])
    op.create_index("ix_tickets_trip_id", "tickets", ["trip_id"])
    op.create_index("ix_tickets_depart_at", "tickets", ["depart_at"])


def downgrade() -> None:
    op.drop_table("tickets")
