"""The one place text becomes a vector.

Everything else calls `embed_texts()`. Swapping the provider is a change to this
file alone.

Two providers, chosen by whether GEMINI_API_KEY is set:

  gemini  -- gemini-embedding-001, truncated to EMBEDDING_DIM and re-normalised.
             Genuinely semantic: "hill station in winter" retrieves a Manali
             trip even with no shared words.
  local   -- hashed character n-grams. No key, no network, deterministic. It
             matches on shared words, not meaning, so it is a development and
             test stand-in, never the thing to demo.

Both return unit vectors of the same length, so the stored column and the index
do not change when you switch.
"""
from __future__ import annotations

import hashlib
import logging
import math
import re
from enum import Enum

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmbedMode(str, Enum):
    """Query and document are embedded differently. That asymmetry is what
    makes top-K retrieval good rather than mediocre."""

    DOCUMENT = "document"
    QUERY = "query"


_GEMINI_TASK_TYPE = {
    EmbedMode.DOCUMENT: "RETRIEVAL_DOCUMENT",
    EmbedMode.QUERY: "RETRIEVAL_QUERY",
}


def embed_texts(texts: list[str], mode: EmbedMode) -> list[list[float]]:
    """Return one unit vector of length `settings.EMBEDDING_DIM` per input."""
    return embed_texts_with_model(texts, mode)[0]


def embed_texts_with_model(texts: list[str], mode: EmbedMode) -> tuple[list[list[float]], str]:
    """The vectors and the name of the model that actually made them.

    If Gemini fails, the local embedder answers instead -- and the name says so,
    so a stored vector is never labelled with a model that did not make it
    (vectors from different models must never be compared)."""
    if not texts:
        return [], current_model_name()

    if settings.GEMINI_API_KEY:
        try:
            return _embed_gemini(texts, mode), settings.EMBEDDING_MODEL
        except Exception as exc:  # noqa: BLE001 -- retrieval must never 500 a request
            logger.warning("Gemini embedding failed, falling back to local: %s", exc)

    return [_embed_local(t) for t in texts], LOCAL_MODEL_NAME


LOCAL_MODEL_NAME = "local-hash-v1"


def current_model_name() -> str:
    """Stored beside every vector. Distances between vectors from two different
    models mean nothing, so retrieval only compares like with like."""
    return settings.EMBEDDING_MODEL if settings.GEMINI_API_KEY else LOCAL_MODEL_NAME


def using_semantic_embeddings() -> bool:
    """False when the local stand-in is in use -- the API surfaces this so the
    UI can say the memory is lexical rather than quietly overselling it."""
    return bool(settings.GEMINI_API_KEY)


# --- Gemini -----------------------------------------------------------------

def _embed_gemini(texts: list[str], mode: EmbedMode) -> list[list[float]]:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    response = client.models.embed_content(
        model=settings.EMBEDDING_MODEL,
        contents=texts,
        config=types.EmbedContentConfig(
            task_type=_GEMINI_TASK_TYPE[mode],
            output_dimensionality=settings.EMBEDDING_DIM,
        ),
    )

    vectors = [list(e.values or []) for e in (response.embeddings or [])]
    if len(vectors) != len(texts):
        raise ValueError(f"Expected {len(texts)} embeddings, got {len(vectors)}")

    # Any output_dimensionality below 3072 comes back unnormalised, and cosine
    # distance assumes unit vectors.
    return [_normalise(v) for v in vectors]


# --- local stand-in ---------------------------------------------------------

_TOKEN_RE = re.compile(r"[a-z0-9]+")

# Words every trip summary contains. Left in, they dominate a lexical vector and
# make a Goa beach trip look 60% similar to a Ladakh trek. The semantic model
# does not need this -- it weighs meaning, not word overlap.
_STOPWORDS = frozenset(
    "a an and the of to in on for with at by from is was are were be it this that "
    "trip trips day days travel traveller travellers traveler travelers "
    "interests interest budget inr rs total per plan visited went "
    "month year style styles preferred".split()
)


def _embed_local(text: str) -> list[float]:
    """Hashed word and character trigrams, L2-normalised.

    Character trigrams as well as words, so "Jaipur" and "jaipurs" land near
    each other instead of sharing nothing.
    """
    dim = settings.EMBEDDING_DIM
    vector = [0.0] * dim

    tokens = [
        tok for tok in _TOKEN_RE.findall(text.lower())
        if tok not in _STOPWORDS and not tok.isdigit()
    ]
    features: list[str] = list(tokens)
    for token in tokens:
        padded = f" {token} "
        features.extend(padded[i : i + 3] for i in range(len(padded) - 2))

    for feature in features:
        digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
        bucket = int.from_bytes(digest[:4], "big") % dim
        # Sign from a separate byte, so unrelated features cancel instead of
        # every vector drifting positive.
        sign = 1.0 if digest[4] & 1 else -1.0
        vector[bucket] += sign

    return _normalise(vector)


def _normalise(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vector))
    if norm == 0:
        return vector
    return [v / norm for v in vector]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """For the SQLite path, where there is no vector operator to lean on.
    Both inputs are already unit vectors, so this is just the dot product."""
    return sum(x * y for x, y in zip(a, b, strict=True))
