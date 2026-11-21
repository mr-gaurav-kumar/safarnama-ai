"""Business / agency accounts, and package ownership.

Revision ID: 0011
Revises: 0010
Create Date: 2026-09-30
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "business_profiles",
        sa.Column("user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("business_name", sa.String(160), nullable=False),
        sa.Column("slug", sa.String(80), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False, server_default="agency"),
        sa.Column("city", sa.String(120), nullable=False),
        sa.Column("phone", sa.String(20), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("website", sa.String(200), nullable=True),
        sa.Column("gst_number", sa.String(15), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("status_reason", sa.String(300), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_business_profiles_slug", "business_profiles", ["slug"], unique=True)
    op.create_index("ix_business_profiles_status", "business_profiles", ["status"])

    with op.batch_alter_table("travel_packages") as batch:
        batch.add_column(sa.Column("owner_id", sa.Uuid(as_uuid=True), nullable=True))
        batch.create_foreign_key("fk_travel_packages_owner", "users", ["owner_id"], ["id"], ondelete="CASCADE")
        batch.create_index("ix_travel_packages_owner_id", ["owner_id"])


def downgrade() -> None:
    with op.batch_alter_table("travel_packages") as batch:
        batch.drop_index("ix_travel_packages_owner_id")
        batch.drop_constraint("fk_travel_packages_owner", type_="foreignkey")
        batch.drop_column("owner_id")
    op.drop_index("ix_business_profiles_status", table_name="business_profiles")
    op.drop_index("ix_business_profiles_slug", table_name="business_profiles")
    op.drop_table("business_profiles")
