"""My documents: travellers' encrypted ID documents.

Revision ID: 0016
Revises: 0015
Create Date: 2026-11-21
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0016"
down_revision: Union[str, None] = "0015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_documents",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("label", sa.String(60), nullable=True),
        sa.Column("number_enc", sa.Text(), nullable=True),
        sa.Column("number_last4", sa.String(4), nullable=True),
        sa.Column("expires_on", sa.Date(), nullable=True),
        sa.Column("file_name", sa.String(80), nullable=True),
        sa.Column("file_type", sa.String(40), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_user_documents_user_id", "user_documents", ["user_id"])


def downgrade() -> None:
    op.drop_table("user_documents")
