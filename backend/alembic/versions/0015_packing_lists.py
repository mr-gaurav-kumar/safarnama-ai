"""Packing lists: per-trip items and the admin's default items.

Revision ID: 0015
Revises: 0014
Create Date: 2026-11-20
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0015"
down_revision: Union[str, None] = "0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "packing_defaults",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("category", sa.String(20), nullable=False, server_default="other"),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("note", sa.String(200), nullable=True),
        sa.Column("user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("created_by", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        *_timestamps(),
    )
    op.create_index("ix_packing_defaults_user_id", "packing_defaults", ["user_id"])

    op.create_table(
        "packing_items",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("trip_id", sa.Uuid(as_uuid=True), sa.ForeignKey("trips.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("category", sa.String(20), nullable=False, server_default="other"),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("packed_going", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("packed_return", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("source", sa.String(10), nullable=False, server_default="mine"),
        sa.Column(
            "default_id", sa.Uuid(as_uuid=True),
            sa.ForeignKey("packing_defaults.id", ondelete="CASCADE"), nullable=True,
        ),
        *_timestamps(),
    )
    op.create_index("ix_packing_items_trip_id", "packing_items", ["trip_id"])
    op.create_index("ix_packing_items_user_id", "packing_items", ["user_id"])
    op.create_index("ix_packing_items_default_id", "packing_items", ["default_id"])


def downgrade() -> None:
    op.drop_table("packing_items")
    op.drop_table("packing_defaults")
