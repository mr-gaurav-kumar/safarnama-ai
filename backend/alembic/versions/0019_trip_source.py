"""Where a trip's plan came from: the AI planner, the traveller, or a copy.

Revision ID: 0019
Revises: 0018
Create Date: 2026-11-21
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0019"
down_revision: Union[str, None] = "0018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("trips") as batch:
        batch.add_column(sa.Column("source", sa.String(10), nullable=False, server_default="ai"))


def downgrade() -> None:
    with op.batch_alter_table("trips") as batch:
        batch.drop_column("source")
