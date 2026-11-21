"""The RAG memory: does retrieval find the right past trips, only the right
user's, and only when asked?"""
from app.rag.embeddings import EmbedMode, cosine_similarity, embed_texts
from tests.helpers import OTHER, SIGNUP, auth, create_trip


def trip(destination, start, end, tags, budget="30000", use_memory=True):
    return {
        "destination": destination, "start_date": start, "end_date": end,
        "budget": budget, "travelers": 2, "style_tags": tags, "use_memory": use_memory,
    }


def sources(body):
    return body["itinerary"]["memory_sources"] or []


# --- the embedder itself ------------------------------------------------------

def test_vectors_are_unit_length_and_the_configured_size():
    [v] = embed_texts(["Goa beach"], EmbedMode.DOCUMENT)
    assert len(v) == 768
    assert abs(sum(x * x for x in v) - 1.0) < 1e-9


def test_similar_trips_score_higher_than_unrelated_ones():
    q, goa, leh = embed_texts(
        [
            "Goa beach holiday, relax and food",
            "Trip to Goa in October. Interests: relax, food. Places: Baga Beach.",
            "Trip to Leh in July. Interests: adventure. Places: Khardung La.",
        ],
        EmbedMode.DOCUMENT,
    )
    assert cosine_similarity(q, goa) > cosine_similarity(q, leh)


# --- retrieval through the API -------------------------------------------------

def test_first_trip_has_no_memory_to_draw_on(client):
    h = auth(client, SIGNUP)
    body = create_trip(client, trip("Goa", "2026-10-01", "2026-10-03", ["relax", "food"]), h)
    assert sources(body) == []


def test_a_similar_past_trip_is_retrieved_for_a_new_one(client):
    h = auth(client, SIGNUP)
    first = create_trip(client, trip("Goa", "2026-10-01", "2026-10-03", ["relax", "food"]), h)

    second = create_trip(client, trip("Goa", "2026-12-20", "2026-12-23", ["food", "relax"]), h)

    hits = sources(second)
    assert [s["trip_id"] for s in hits] == [first["id"]]
    assert hits[0]["destination"] == "Goa"
    assert 0 < hits[0]["similarity"] <= 1


def test_the_closer_trip_ranks_first(client):
    h = auth(client, SIGNUP)
    create_trip(client, trip("Leh", "2026-07-01", "2026-07-07", ["adventure", "nature"]), h)
    goa = create_trip(client, trip("Goa", "2026-10-01", "2026-10-03", ["relax", "food"]), h)

    new = create_trip(client, trip("Goa", "2026-12-20", "2026-12-23", ["relax", "food"]), h)

    hits = sources(new)
    assert hits, "the earlier Goa trip should be recalled"
    assert hits[0]["trip_id"] == goa["id"], "Goa must outrank Leh for a Goa request"


def test_an_unrelated_past_trip_is_not_forced_in(client):
    """Below the similarity floor a past trip is noise. Better no memory than
    a Ladakh trek shaping a Goa beach plan."""
    h = auth(client, SIGNUP)
    create_trip(client, trip("Leh", "2026-07-01", "2026-07-07", ["adventure", "nature"]), h)

    new = create_trip(client, trip("Goa", "2026-12-20", "2026-12-23", ["relax", "food"]), h)
    assert sources(new) == []


def test_memory_never_crosses_users(client):
    mine = auth(client, SIGNUP)
    create_trip(client, trip("Goa", "2026-10-01", "2026-10-03", ["relax", "food"]), mine)

    theirs = auth(client, OTHER)
    body = create_trip(client, trip("Goa", "2026-12-20", "2026-12-23", ["relax", "food"]), theirs)
    assert sources(body) == [], "Riya's plan must not be shaped by Garv's trips"


def test_turning_memory_off_skips_retrieval(client):
    h = auth(client, SIGNUP)
    create_trip(client, trip("Goa", "2026-10-01", "2026-10-03", ["relax", "food"]), h)

    body = create_trip(client, trip("Goa", "2026-12-20", "2026-12-23", ["relax", "food"], use_memory=False), h)
    assert sources(body) == []


def test_deleting_a_trip_removes_it_from_memory(client, db_session):
    from app.models.embedding import TripEmbedding

    h = auth(client, SIGNUP)
    first = create_trip(client, trip("Goa", "2026-10-01", "2026-10-03", ["relax", "food"]), h)
    assert db_session.query(TripEmbedding).count() == 1

    client.delete(f"/trips/{first['id']}", headers=h)
    db_session.expire_all()
    assert db_session.query(TripEmbedding).count() == 0, "the row itself must go, not just be hidden"

    body = create_trip(client, trip("Goa", "2026-12-20", "2026-12-23", ["relax", "food"]), h)
    assert sources(body) == [], "a deleted trip must not be recalled"


def test_every_completed_trip_is_stored_once(client, db_session):
    from app.models.embedding import TripEmbedding

    h = auth(client, SIGNUP)
    create_trip(client, trip("Goa", "2026-10-01", "2026-10-03", ["relax"]), h)
    create_trip(client, trip("Jaipur", "2026-11-01", "2026-11-03", ["culture"]), h)

    rows = db_session.query(TripEmbedding).all()
    assert len(rows) == 2
    assert all(r.model == "local-hash-v1" for r in rows)
    assert all(r.source_text.startswith("Trip to") for r in rows)


def test_postgres_query_compiles_with_the_pgvector_operator():
    """The SQLite suite never executes the Postgres ranking path, so compile it
    here. A variant column type once made `.cosine_distance()` vanish on
    Postgres while every other test stayed green."""
    import uuid

    from sqlalchemy import select
    from sqlalchemy.dialects import postgresql

    from app.models.embedding import TripEmbedding
    from app.rag.retrieval import cosine_distance_expr

    distance = cosine_distance_expr([0.0] * 768)
    stmt = (
        select(TripEmbedding.trip_id)
        .where(TripEmbedding.user_id == uuid.uuid4())
        .order_by(distance)
        .limit(3)
    )
    sql = str(stmt.compile(dialect=postgresql.dialect()))
    assert "<=>" in sql
    assert "ORDER BY" in sql and "LIMIT" in sql
