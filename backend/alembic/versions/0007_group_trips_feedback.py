"""Group trips, trip rooms, feedback and match requests.

Revision ID: 0007
Revises: 0006
Create Date: 2026-09-24
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

JSONColumn = sa.JSON().with_variant(postgresql.JSONB, "postgresql")


def _ts() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    ]


def _fk(name: str, table: str, *, nullable: bool = False, index: bool = False) -> sa.Column:
    return sa.Column(name, sa.Uuid(as_uuid=True),
                     sa.ForeignKey(f"{table}.id", ondelete="CASCADE"), nullable=nullable)


def upgrade() -> None:
    op.create_table(
        "trip_collaborators",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        _fk("trip_id", "trips"),
        sa.Column("invited_email", sa.String(255), nullable=False),
        _fk("user_id", "users", nullable=True),
        sa.Column("status", sa.String(10), nullable=False, server_default="invited"),
        sa.Column("invite_token_hash", sa.String(64), nullable=False, unique=True),
        _fk("invited_by", "users"),
        sa.Column("style_tags", JSONColumn, nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=True),
        *_ts(),
        sa.UniqueConstraint("trip_id", "invited_email"),
    )
    op.create_index("ix_trip_collaborators_trip_id", "trip_collaborators", ["trip_id"])
    op.create_index("ix_trip_collaborators_user_id", "trip_collaborators", ["user_id"])
    op.create_index("ix_trip_collaborators_invited_email", "trip_collaborators", ["invited_email"])

    op.create_table(
        "trip_room_messages",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        _fk("trip_id", "trips"),
        _fk("user_id", "users"),
        sa.Column("message", sa.Text(), nullable=False),
        *_ts(),
    )
    op.create_index("ix_trip_room_messages_trip_created", "trip_room_messages", ["trip_id", "created_at"])

    op.create_table(
        "trip_feedback",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        _fk("trip_id", "trips"),
        _fk("user_id", "users"),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        *_ts(),
        sa.UniqueConstraint("trip_id", "user_id"),
        sa.CheckConstraint("rating BETWEEN 1 AND 5", name="ck_trip_feedback_rating"),
    )
    op.create_index("ix_trip_feedback_trip_id", "trip_feedback", ["trip_id"])

    op.create_table(
        "trip_match_requests",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        _fk("from_trip_id", "trips"),
        _fk("to_trip_id", "trips"),
        _fk("from_user_id", "users"),
        *_ts(),
        sa.UniqueConstraint("from_trip_id", "to_trip_id"),
    )
    op.create_index("ix_trip_match_requests_to_trip_id", "trip_match_requests", ["to_trip_id"])
    op.create_index("ix_trip_match_requests_from_user_id", "trip_match_requests", ["from_user_id"])

    with op.batch_alter_table("trips") as batch:
        batch.add_column(sa.Column("discoverable", sa.Boolean(), nullable=False, server_default=sa.false()))
    # Overlap search: same destination, overlapping dates, opted in.
    op.create_index("ix_trips_discoverable_start", "trips", ["discoverable", "start_date"])

    with op.batch_alter_table("trip_embeddings") as batch:
        batch.add_column(sa.Column("rating", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("trip_embeddings") as batch:
        batch.drop_column("rating")
    op.drop_index("ix_trips_discoverable_start", table_name="trips")
    with op.batch_alter_table("trips") as batch:
        batch.drop_column("discoverable")
    for table in ("trip_match_requests", "trip_feedback", "trip_room_messages", "trip_collaborators"):
        op.drop_table(table)
