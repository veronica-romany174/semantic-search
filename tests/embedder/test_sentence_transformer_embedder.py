"""
tests/embedder/test_sentence_transformer_embedder.py

Tests for SentenceTransformerEmbedder.

Uses the real model — fast after the first download (~90 MB, cached by HuggingFace).
All tests are isolated; no vector store or disk access required.
"""

import math

import pytest

from app.embedder.sentence_transformer_embedder import SentenceTransformerEmbedder


# ── Helpers ────────────────────────────────────────────────────────────────────

def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x ** 2 for x in a))
    norm_b = math.sqrt(sum(x ** 2 for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


# Module-level fixture — model is loaded once for the whole test module,
# making the suite fast after the initial download.
@pytest.fixture(scope="module")
def embedder() -> SentenceTransformerEmbedder:
    return SentenceTransformerEmbedder()


# ── Tests ──────────────────────────────────────────────────────────────────────

class TestSentenceTransformerEmbedder:

    def test_model_is_not_loaded_at_construction(self) -> None:
        """
        The model must not be loaded at __init__ time (lazy loading).
        This keeps server startup instant even before the first request.
        """
        fresh = SentenceTransformerEmbedder()
        assert fresh._model is None

    def test_embed_texts_returns_correct_shape(self, embedder) -> None:
        """
        embed_texts(n items) must return n vectors, each of the same dimension.
        """
        texts = ["hello world", "semantic search is cool"]
        results = embedder.embed_texts(texts)

        assert len(results) == 2
        assert len(results[0]) == len(results[1])  # same dimension
        assert len(results[0]) > 0                 # non-empty vectors

    def test_embed_texts_empty_list_returns_empty(self, embedder) -> None:
        """embed_texts([]) must return [] without raising."""
        assert embedder.embed_texts([]) == []

    def test_embed_query_returns_single_flat_vector(self, embedder) -> None:
        """embed_query must return a flat list[float], not list[list[float]]."""
        vec = embedder.embed_query("what is machine learning?")

        assert isinstance(vec, list)
        assert len(vec) > 0
        assert isinstance(vec[0], float)

    def test_embed_query_and_embed_texts_produce_same_dimension(self, embedder) -> None:
        """
        Query and document embeddings must live in the same vector space
        (same dimension) so similarity search works correctly.
        """
        doc_vec = embedder.embed_texts(["some document chunk"])[0]
        query_vec = embedder.embed_query("some document chunk")

        assert len(doc_vec) == len(query_vec)

    def test_similar_texts_have_higher_similarity(self, embedder) -> None:
        """
        Semantically similar texts must score higher than dissimilar ones.
        This is the core property that makes semantic search useful.
        """
        query = embedder.embed_query("machine learning algorithms")
        similar = embedder.embed_texts(["deep learning is a subset of machine learning"])[0]
        dissimilar = embedder.embed_texts(["the recipe calls for two cups of flour"])[0]

        sim_relevant = cosine_similarity(query, similar)
        sim_noise = cosine_similarity(query, dissimilar)

        assert sim_relevant > sim_noise, (
            f"Expected similar ({sim_relevant:.4f}) > dissimilar ({sim_noise:.4f})"
        )

    def test_vectors_are_normalised(self, embedder) -> None:
        """
        all-MiniLM-L6-v2 produces unit-length vectors by default.
        Normalised embeddings are required for cosine similarity via dot product.
        """
        vec = embedder.embed_query("test normalisation")
        norm = math.sqrt(sum(x ** 2 for x in vec))

        assert abs(norm - 1.0) < 1e-4, f"Expected unit vector, got norm={norm:.6f}"

    def test_model_is_loaded_after_first_call(self, embedder) -> None:
        """
        The _model attribute must be populated after the first embed call.
        (Guarantees the lazy-load mechanism actually runs.)
        """
        # The module-scoped fixture has already called embed at least once.
        assert embedder._model is not None
