"""Activity events, fraud flags and the admin audit log.

Revision ID: 0008
Revises: 0007
Create Date: 2026-09-24
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008"
down_revision: Union[str, None] = "0007"
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
        "activity_events",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("ip", sa.String(45), nullable=True),
        sa.Column("trip_id", sa.Uuid(as_uuid=True), nullable=True),
        *_ts(),
    )
    op.create_index("ix_activity_events_user_kind_created", "activity_events", ["user_id", "kind", "created_at"])
    op.create_index("ix_activity_events_ip_kind_created", "activity_events", ["ip", "kind", "created_at"])

    op.create_table(
        "fraud_flags",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("trip_id", sa.Uuid(as_uuid=True), sa.ForeignKey("trips.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reason", sa.String(40), nullable=False),
        sa.Column("risk_score", sa.Float(), nullable=False),
        sa.Column("details", JSONColumn, nullable=False),
        sa.Column("status", sa.String(10), nullable=False, server_default="open"),
        sa.Column("reviewed_by", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        *_ts(),
    )
    op.create_index("ix_fraud_flags_user_id", "fraud_flags", ["user_id"])
    op.create_index("ix_fraud_flags_status", "fraud_flags", ["status"])

    op.create_table(
        "admin_actions",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("admin_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(40), nullable=False),
        sa.Column("target_type", sa.String(20), nullable=False),
        sa.Column("target_id", sa.String(64), nullable=False),
        sa.Column("details", JSONColumn, nullable=False),
        *_ts(),
    )
    op.create_index("ix_admin_actions_admin_id", "admin_actions", ["admin_id"])


def downgrade() -> None:
    op.drop_table("admin_actions")
    op.drop_table("fraud_flags")
    op.drop_table("activity_events")
