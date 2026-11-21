"""Create chat_logs and support_escalations.

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-23
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    ]


def upgrade() -> None:
    op.create_table(
        "chat_logs",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.Uuid(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sender", sa.String(10), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("intent", sa.String(40), nullable=True),
        sa.Column("sentiment", sa.String(10), nullable=True),
        *_timestamps(),
    )
    # History is always read per user, newest first.
    op.create_index("ix_chat_logs_user_created", "chat_logs", ["user_id", "created_at"])

    op.create_table(
        "support_escalations",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.Uuid(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reason", sa.String(30), nullable=False),
        sa.Column("intent", sa.String(40), nullable=True),
        sa.Column("excerpt", sa.Text(), nullable=False),
        sa.Column("status", sa.String(12), nullable=False, server_default="open"),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
    )
    op.create_index("ix_support_escalations_user_id", "support_escalations", ["user_id"])
    op.create_index("ix_support_escalations_status", "support_escalations", ["status"])


def downgrade() -> None:
    op.drop_index("ix_support_escalations_status", table_name="support_escalations")
    op.drop_index("ix_support_escalations_user_id", table_name="support_escalations")
    op.drop_table("support_escalations")
    op.drop_index("ix_chat_logs_user_created", table_name="chat_logs")
    op.drop_table("chat_logs")
