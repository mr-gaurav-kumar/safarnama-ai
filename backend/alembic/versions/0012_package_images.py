"""Photos on travel packages.

Revision ID: 0012
Revises: 0011
Create Date: 2026-09-30
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0012"
down_revision: Union[str, None] = "0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

JSONColumn = sa.JSON().with_variant(postgresql.JSONB, "postgresql")


def upgrade() -> None:
    op.add_column("travel_packages", sa.Column("images", JSONColumn, nullable=False, server_default="[]"))


def downgrade() -> None:
    with op.batch_alter_table("travel_packages") as batch:
        batch.drop_column("images")
