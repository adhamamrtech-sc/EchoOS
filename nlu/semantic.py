"""Semantic search using multilingual embeddings."""

from .catalog import EXAMPLE_OWNERS, EXAMPLE_TEXTS


MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

_model = None
_model_failed = False
_example_vectors = None

EXAMPLE_KEYS = [command.key for command in EXAMPLE_OWNERS]


def get_model():
    """Load the embedding model only once."""
    global _model
    global _model_failed

    if _model is None and not _model_failed:
        try:
            from sentence_transformers import SentenceTransformer

            _model = SentenceTransformer(MODEL_NAME)
        except Exception as error:
            _model_failed = True
            print(f"[nlu] Semantic search disabled: {error}")

    return _model


def get_example_vectors():
    """Encode catalog examples once and cache them."""
    global _example_vectors

    model = get_model()

    if model is None:
        return None

    if _example_vectors is None:
        _example_vectors = model.encode(
            EXAMPLE_TEXTS,
            normalize_embeddings=True,
        )

    return _example_vectors


def warm_up() -> None:
    """Optional startup warm-up."""
    get_example_vectors()


def cosine_similarity(query_vector, matrix):
    query_norm = np.linalg.norm(query_vector)
    matrix_norms = np.linalg.norm(matrix, axis=1)
    denominator = np.maximum(matrix_norms * query_norm, 1e-10)
    return (matrix @ query_vector) / denominator


def semantic_search(text: str) -> dict[str, float]:
    """Return the best semantic score for each command."""
    if not text:
        return {}

    model = get_model()

    if model is None:
        return {}

    example_vectors = get_example_vectors()

    if example_vectors is None:
        return {}

    query_vector = model.encode(text, normalize_embeddings=True)
    similarities = cosine_similarity(query_vector, example_vectors)
    scores = {}

    for key, similarity in zip(EXAMPLE_KEYS, similarities):
        similarity = float(similarity)
        normalized_score = (similarity + 1.0) / 2.0
        scores[key] = max(scores.get(key, 0.0), normalized_score)

    return scores
