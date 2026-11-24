"""Semantic search using multilingual embeddings (lazy, optional).

Nothing heavy happens at import time. The model is loaded only the first
time semantic_search() is actually called, which happens only when the
rules and RapidFuzz were not confident enough.
"""

import os
import threading

from .catalog import EXAMPLE_OWNERS, EXAMPLE_TEXTS


MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

_model = None
_model_failed = False
_example_vectors = None
_lock = threading.Lock()

EXAMPLE_KEYS = [command.key for command in EXAMPLE_OWNERS]


def is_enabled() -> bool:
    """False when turned off with ECHOOS_SEMANTIC=0. Never loads anything."""
    value = os.environ.get("ECHOOS_SEMANTIC", "1").strip().lower()
    return value not in ("0", "false", "off", "no") and not _model_failed


def is_loaded() -> bool:
    """True once the model is in memory. Never triggers loading."""
    return _example_vectors is not None


def _load() -> bool:
    """Load the model and encode the catalog examples. Runs at most once."""
    global _model, _model_failed, _example_vectors

    with _lock:
        if _example_vectors is not None:
            return True

        if not is_enabled():
            return False

        try:
            from sentence_transformers import SentenceTransformer

            _model = SentenceTransformer(MODEL_NAME)
            _example_vectors = _model.encode(
                EXAMPLE_TEXTS,
                normalize_embeddings=True,
            )
        except ImportError:
            _model_failed = True
            print("[nlu] sentence-transformers not installed: fuzzy matching only.")
        except Exception as error:
            _model_failed = True
            print(f"[nlu] Semantic search disabled: {error}")

        return _example_vectors is not None


def warm_up() -> bool:
    """Optional: load now instead of on first use. Not called by default."""
    return _load()


def semantic_search(text: str) -> dict[str, float]:
    """Return the best semantic score (0..1) for each command."""
    if not text:
        return {}

    if _example_vectors is None and not _load():
        return {}

    try:
        query_vector = _model.encode(text, normalize_embeddings=True)
    except Exception as error:
        print(f"[nlu] Semantic search failed: {error}")
        return {}

    # Both sides are unit vectors, so dot product == cosine similarity.
    similarities = _example_vectors @ query_vector
    scores = {}

    for key, similarity in zip(EXAMPLE_KEYS, similarities):
        normalized_score = (float(similarity) + 1.0) / 2.0
        scores[key] = max(scores.get(key, 0.0), normalized_score)

    return scores