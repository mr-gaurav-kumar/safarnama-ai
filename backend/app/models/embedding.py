"""trip_embeddings -- the RAG "memory" table, §5.1 of the project document.

One row per completed trip: the text that was embedded and its vector. Retrieval
compares a new request against a user's own rows only.
"""
import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, ForeignKey, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import settings
from app.models.base import Base, TimestampMixin, UUIDMixin

# A real pgvector column on Postgres, so the `<=>` operator and the HNSW index
# work. A JSON array everywhere else, so development and tests run on SQLite.
# The Python value is a list[float] either way.
EmbeddingColumn = JSON().with_variant(Vector(settings.EMBEDDING_DIM), "postgresql")


class TripEmbedding(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "trip_embeddings"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        index=True, nullable=False,
    )
    # One embedding per trip; regenerating a trip replaces its row.
    trip_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("trips.id", ondelete="CASCADE"),
        unique=True, nullable=False,
    )

    embedding: Mapped[list[float]] = mapped_column(EmbeddingColumn, nullable=False)

    # Exactly what was embedded. Kept so retrieval results can be shown to the
    # LLM and to the user, and so the vectors can be rebuilt if the model changes.
    source_text: Mapped[str] = mapped_column(Text, nullable=False)

    # Which model produced the vector. Mixing vectors from two models in one
    # search gives meaningless distances, so retrieval filters on this.
    model: Mapped[str] = mapped_column(Text, nullable=False)

    # The owner's 1-5 rating once the trip is over. Retrieval weighs trips the
    # traveller loved up and ones they disliked down (the feedback loop, §4.11).
    rating: Mapped[int | None] = mapped_column(nullable=True)
