"""
tests/vector_store/test_chroma_store.py

Unit tests for ChromaVectorStore.

All tests use a temporary directory (tmp_path) so they never touch
the real ./data/chroma directory and are fully isolated from each other.
"""

import pytest

from app.core.exceptions import VectorStoreError
from app.vector_store.base import TextChunk
from app.vector_store.chroma_store import ChromaVectorStore


# ── Helpers ────────────────────────────────────────────────────────────────────

DIM = 4  # tiny embedding dimension — fast for tests


def _store(tmp_path) -> ChromaVectorStore:
    """Return a fresh ChromaVectorStore backed by a temp directory."""
    return ChromaVectorStore(
        persist_dir=str(tmp_path / "chroma"),
        collection_name="test_collection",
    )


def _chunk(
    text: str = "hello world",
    source: str = "doc.pdf",
    page: int = 1,
    idx: int = 0,
    embedding: list | None = None,
) -> TextChunk:
    return TextChunk(
        text=text,
        source_file=source,
        page_number=page,
        chunk_index=idx,
        embedding=embedding or [0.1, 0.2, 0.3, 0.4],
    )


# ── Tests ──────────────────────────────────────────────────────────────────────

class TestChromaVectorStore:

    def test_upsert_then_query_returns_result(self, tmp_path) -> None:
        """
        After upserting a chunk we should be able to retrieve it via query.
        The returned StoreResult must match the stored text and metadata.
        """
        store = _store(tmp_path)
        chunk = _chunk(text="semantic search is amazing")
        store.upsert([chunk])

        results = store.query(embedding=[0.1, 0.2, 0.3, 0.4], top_k=1)

        assert len(results) == 1
        assert results[0].text == "semantic search is amazing"
        assert results[0].source_file == "doc.pdf"
        assert results[0].page_number == 1

    def test_query_returns_most_similar_first(self, tmp_path) -> None:
        """
        When two chunks are stored the one whose embedding is closest to the
        query vector must be ranked first.
        """
        store = _store(tmp_path)
        # chunk_a embedding is identical to the query → highest similarity
        chunk_a = _chunk(text="very relevant", idx=0, embedding=[1.0, 0.0, 0.0, 0.0])
        # chunk_b is orthogonal → lower similarity
        chunk_b = _chunk(text="less relevant", idx=1, embedding=[0.0, 1.0, 0.0, 0.0])
        store.upsert([chunk_a, chunk_b])

        results = store.query(embedding=[1.0, 0.0, 0.0, 0.0], top_k=2)

        assert results[0].text == "very relevant"
        assert results[0].score > results[1].score

    def test_upsert_is_idempotent(self, tmp_path) -> None:
        """
        Re-upserting the same chunk id twice must not duplicate documents.
        The collection should contain exactly one entry.
        """
        store = _store(tmp_path)
        chunk = _chunk()
        store.upsert([chunk])
        store.upsert([chunk])  # second upsert with same id

        results = store.query(embedding=[0.1, 0.2, 0.3, 0.4], top_k=10)
        assert len(results) == 1

    def test_clear_empties_collection(self, tmp_path) -> None:
        """
        After clear() a query must return an empty list.
        """
        store = _store(tmp_path)
        store.upsert([_chunk(idx=0), _chunk(idx=1)])
        store.clear()

        results = store.query(embedding=[0.1, 0.2, 0.3, 0.4], top_k=5)
        assert results == []

    def test_clear_on_empty_collection_is_safe(self, tmp_path) -> None:
        """Calling clear() on an already-empty collection must not raise."""
        store = _store(tmp_path)
        store.clear()  # should be a no-op

    def test_upsert_without_embedding_raises(self, tmp_path) -> None:
        """
        A chunk with an empty embedding list must raise VectorStoreError
        before touching the backend.
        """
        store = _store(tmp_path)
        bad_chunk = TextChunk(
            text="no embedding here",
            source_file="doc.pdf",
            page_number=1,
            chunk_index=0,
            embedding=[],  # missing!
        )

        with pytest.raises(VectorStoreError, match="missing embeddings"):
            store.upsert([bad_chunk])

    def test_chunk_id_is_deterministic(self) -> None:
        """
        TextChunk.id must be stable so the same chunk always maps to the
        same document id in Chroma (ensuring idempotent upserts).
        """
        c1 = _chunk(source="report.pdf", page=3, idx=2)
        c2 = _chunk(source="report.pdf", page=3, idx=2)
        assert c1.id == c2.id
        assert c1.id == "report.pdf__p3__c2"

    def test_score_is_between_minus_one_and_one(self, tmp_path) -> None:
        """
        Cosine similarity must be in [-1, 1].
        """
        store = _store(tmp_path)
        store.upsert([_chunk()])
        results = store.query(embedding=[0.1, 0.2, 0.3, 0.4], top_k=1)
        assert -1.0 <= results[0].score <= 1.0
