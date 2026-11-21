"""Store a trip in memory, and find the user's past trips that resemble a new one.

This is the R in RAG. `find_similar_trips` is the retrieval step; the result is
turned into prompt text by `build_memory_context` and handed to the planner.

On Postgres the ranking happens in the database with pgvector's `<=>` cosine
distance operator and the HNSW index. On SQLite (development and tests) there is
no vector type, so the same ranking is done in Python. Both paths return the
same shape, and both only ever look at one user's own trips.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date

from pgvector.sqlalchemy import Vector
from sqlalchemy import Float, literal, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.embedding import TripEmbedding
from app.models.trip import Trip
from app.rag.embeddings import EmbedMode, cosine_similarity, current_model_name, embed_texts, embed_texts_with_model

MAX_PLACES_IN_SUMMARY = 12


@dataclass(frozen=True)
class MemoryHit:
    trip_id: uuid.UUID
    destination: str
    start_date: date
    similarity: float
    source_text: str
    rating: int | None = None

    @property
    def score(self) -> float:
        """Similarity nudged by how the trip went -- the feedback loop. A loved
        trip that is a little less similar can outrank a disliked one."""
        return self.similarity * RATING_WEIGHT.get(self.rating, 1.0)


# How much a 1-5 rating moves a past trip up or down the ranking.
RATING_WEIGHT: dict[int | None, float] = {5: 1.2, 4: 1.08, 3: 1.0, 2: 0.85, 1: 0.7, None: 1.0}
MAX_COMMENT_CHARS = 300


# --- what gets embedded -----------------------------------------------------

def _season(d: date) -> str:
    return d.strftime("%B")


def summarise_trip(trip: Trip) -> str:
    """The document side: a completed trip, in words, including where the
    person actually went. This text is what future requests are compared to."""
    days = (trip.end_date - trip.start_date).days + 1
    parts = [
        f"Trip to {trip.destination} in {_season(trip.start_date)}.",
        f"{days} days, {trip.travelers} travellers.",
    ]
    if trip.style_tags:
        parts.append(f"Interests: {', '.join(trip.style_tags)}.")
    parts.append(f"Budget INR {float(trip.budget):,.0f}.")

    places = _places_from_itinerary(trip)
    if places:
        parts.append(f"Places: {', '.join(places)}.")

    rating, comment = _owner_feedback(trip)
    if rating is not None:
        parts.append(f"Traveller rated it {rating}/5.")
        if comment:
            parts.append(f'They said: "{comment[:MAX_COMMENT_CHARS]}".')

    return " ".join(parts)


def _owner_feedback(trip: Trip) -> tuple[int | None, str | None]:
    """Only the owner's rating shapes the owner's memory."""
    from sqlalchemy.orm import object_session

    from app.models.group import TripFeedback

    db = object_session(trip)
    if db is None:
        return None, None
    fb = db.scalar(select(TripFeedback).where(
        TripFeedback.trip_id == trip.id, TripFeedback.user_id == trip.user_id
    ))
    return (fb.rating, (fb.comment or "").strip() or None) if fb else (None, None)


def summarise_request(
    *, destination: str, start_date: date, end_date: date,
    style_tags: list[str], budget: float,
) -> str:
    """The query side: what the person is asking for now. Deliberately shorter
    than a trip summary -- a query carries intent, not a record."""
    days = (end_date - start_date).days + 1
    tags = f" Interests: {', '.join(style_tags)}." if style_tags else ""
    return (
        f"Trip to {destination} in {_season(start_date)}, {days} days."
        f"{tags} Budget INR {budget:,.0f}."
    )


def _places_from_itinerary(trip: Trip) -> list[str]:
    if trip.itinerary is None:
        return []
    seen: list[str] = []
    for day in trip.itinerary.day_plan or []:
        for item in day.get("items", []):
            place = str(item.get("place", "")).strip()
            # The fallback planner repeats the destination as every "place";
            # that says nothing new, so leave it out.
            if place and place.lower() != trip.destination.lower() and place not in seen:
                seen.append(place)
    return seen[:MAX_PLACES_IN_SUMMARY]


# --- store --------------------------------------------------------------------

def store_trip_embedding(db: Session, trip: Trip) -> TripEmbedding:
    """Embed a completed trip and save it, replacing any earlier row for it.
    This is how memory grows: every finished trip becomes retrievable."""
    text = summarise_trip(trip)
    [vector], model = embed_texts_with_model([text], EmbedMode.DOCUMENT)

    row = db.scalar(select(TripEmbedding).where(TripEmbedding.trip_id == trip.id))
    if row is None:
        row = TripEmbedding(user_id=trip.user_id, trip_id=trip.id)
        db.add(row)

    row.embedding = vector
    row.source_text = text
    row.model = model
    row.rating = _owner_feedback(trip)[0]
    db.commit()
    db.refresh(row)
    return row


# --- retrieve -----------------------------------------------------------------

def find_similar_trips(
    db: Session,
    *,
    user_id: uuid.UUID,
    query_text: str,
    exclude_trip_id: uuid.UUID | None = None,
    top_k: int | None = None,
    min_similarity: float | None = None,
) -> list[MemoryHit]:
    """The user's past trips most similar to `query_text`, best first.

    Scoped to `user_id` -- one person's memory never leaks into another's plan.
    Only vectors from the current embedding model are compared.
    """
    top_k = settings.MEMORY_TOP_K if top_k is None else top_k
    floor = settings.MEMORY_MIN_SIMILARITY if min_similarity is None else min_similarity

    [query_vector], model = embed_texts_with_model([query_text], EmbedMode.QUERY)

    stmt = (
        select(TripEmbedding, Trip.destination, Trip.start_date)
        .join(Trip, Trip.id == TripEmbedding.trip_id)
        .where(
            TripEmbedding.user_id == user_id,
            TripEmbedding.model == model,
        )
    )
    if exclude_trip_id is not None:
        stmt = stmt.where(TripEmbedding.trip_id != exclude_trip_id)

    # Over-fetch, then re-rank by rating-weighted score -- the database orders
    # by pure similarity, and ratings can reorder the top few.
    fetch = max(top_k * 3, top_k)
    if db.get_bind().dialect.name == "postgresql":
        hits = _rank_in_postgres(db, stmt, query_vector, fetch)
    else:
        hits = _rank_in_python(db, stmt, query_vector, fetch)

    hits = [h for h in hits if h.similarity >= floor]
    hits.sort(key=lambda h: h.score, reverse=True)
    return hits[:top_k]


def cosine_distance_expr(query_vector: list[float]):
    """`embedding <=> :query` -- pgvector's cosine *distance* (0 = identical).

    Spelled out with `.op()` rather than pgvector's `.cosine_distance()` helper:
    the column's type is a JSON/Vector variant so SQLite can run the tests, and
    SQLAlchemy takes a variant's operators from the base type -- JSON, which has
    no vector operators. The query vector is bound as a real `vector` so the
    HNSW index is used.
    """
    query = literal(query_vector, type_=Vector(settings.EMBEDDING_DIM))
    return TripEmbedding.embedding.op("<=>", return_type=Float)(query)


def _rank_in_postgres(db, stmt, query_vector, top_k) -> list[MemoryHit]:
    # Similarity is 1 - cosine distance.
    distance = cosine_distance_expr(query_vector)
    rows = db.execute(stmt.add_columns(distance.label("distance")).order_by(distance).limit(top_k))
    return [
        MemoryHit(
            trip_id=emb.trip_id, destination=dest, start_date=start,
            similarity=1.0 - float(dist), source_text=emb.source_text, rating=emb.rating,
        )
        for emb, dest, start, dist in rows
    ]


def _rank_in_python(db, stmt, query_vector, top_k) -> list[MemoryHit]:
    scored = [
        MemoryHit(
            trip_id=emb.trip_id, destination=dest, start_date=start,
            similarity=cosine_similarity(query_vector, emb.embedding),
            source_text=emb.source_text, rating=emb.rating,
        )
        for emb, dest, start in db.execute(stmt)
    ]
    scored.sort(key=lambda h: h.similarity, reverse=True)
    return scored[:top_k]


# --- augment ------------------------------------------------------------------

def build_memory_context(hits: list[MemoryHit]) -> str | None:
    """Turn retrieved trips into the paragraph the planner reads. None when
    there is nothing relevant, so the prompt carries no empty memory section."""
    if not hits:
        return None
    return " | ".join(h.source_text for h in hits)
