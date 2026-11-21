"""Create trip_embeddings, the RAG memory table.

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-23
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Must match settings.EMBEDDING_DIM. Changing it later means re-embedding every
# stored trip, so it is pinned here rather than read from config at migrate time.
EMBEDDING_DIM = 768


def upgrade() -> None:
    is_postgres = op.get_bind().dialect.name == "postgresql"

    if is_postgres:
        from pgvector.sqlalchemy import Vector
        embedding_type = Vector(EMBEDDING_DIM)
    else:
        embedding_type = sa.JSON()

    op.create_table(
        "trip_embeddings",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.Uuid(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("trip_id", sa.Uuid(as_uuid=True),
                  sa.ForeignKey("trips.id", ondelete="CASCADE"),
                  nullable=False, unique=True),
        sa.Column("embedding", embedding_type, nullable=False),
        sa.Column("source_text", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index("ix_trip_embeddings_user_id", "trip_embeddings", ["user_id"])

    # Which past trips shaped each itinerary -- the "why" behind the plan.
    with op.batch_alter_table("itineraries") as batch:
        batch.add_column(sa.Column(
            "memory_sources",
            sa.JSON().with_variant(postgresql.JSONB, "postgresql"),
            nullable=True,
        ))

    if is_postgres:
        # HNSW rather than IVFFlat: it needs no training data, so it works from
        # the first row instead of only after a few hundred.
        op.execute(
            "CREATE INDEX ix_trip_embeddings_embedding_hnsw "
            "ON trip_embeddings USING hnsw (embedding vector_cosine_ops)"
        )


def downgrade() -> None:
    with op.batch_alter_table("itineraries") as batch:
        batch.drop_column("memory_sources")
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP INDEX IF EXISTS ix_trip_embeddings_embedding_hnsw")
    op.drop_index("ix_trip_embeddings_user_id", table_name="trip_embeddings")
    op.drop_table("trip_embeddings")
