"""
tests/services/test_search_service.py

Unit tests for SearchService.

Embedder and VectorStore are replaced with MagicMock objects so tests
are fast, deterministic, and have zero external I/O.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.core.exceptions import EmptyQueryError, SearchError
from app.models.search_models import SearchResponse, SearchResult
from app.services.search_service import SearchService
from app.vector_store.base import StoreResult


# ── Helpers ────────────────────────────────────────────────────────────────────

def _store_result(text: str, source: str = "doc.pdf", page: int = 1, score: float = 0.9) -> StoreResult:
    return StoreResult(text=text, source_file=source, page_number=page, score=score)


def _make_service(
    store_results: list[StoreResult] | None = None,
    vector: list[float] | None = None,
) -> SearchService:
    """Build SearchService with mocked embedder + store."""
    store_results = store_results if store_results is not None else [
        _store_result("Vector databases store embeddings.", score=0.95),
        _store_result("Semantic search is powerful.", score=0.80),
    ]
    vector = vector or [0.1] * 384

    embedder = MagicMock()
    embedder.embed_query.return_value = vector

    store = MagicMock()
    store.query.return_value = store_results

    return SearchService(embedder=embedder, store=store)


# ── Tests ──────────────────────────────────────────────────────────────────────

class TestSearchService:

    @pytest.mark.asyncio
    async def test_happy_path_returns_search_response(self) -> None:
        """A valid query returns a SearchResponse with mapped results."""
        service = _make_service()
        result = await service.search("What is a vector database?")

        assert isinstance(result, SearchResponse)
        assert len(result.results) == 2

    @pytest.mark.asyncio
    async def test_results_map_fields_correctly(self) -> None:
        """StoreResult fields are mapped to SearchResult fields correctly."""
        sr = _store_result("Some content.", source="report.pdf", score=0.88)
        service = _make_service(store_results=[sr])

        result = await service.search("any query")

        item = result.results[0]
        assert isinstance(item, SearchResult)
        assert item.document == "report.pdf"
        assert item.content == "Some content."
        assert item.score == round(0.88, 4)

    @pytest.mark.asyncio
    async def test_embedder_called_with_stripped_query(self) -> None:
        """The query is stripped of whitespace before being embedded."""
        service = _make_service()

        await service.search("  hello world  ")

        service._embedder.embed_query.assert_called_once_with("hello world")

    @pytest.mark.asyncio
    async def test_default_top_k_used_when_not_supplied(self) -> None:
        """When top_k is None, the store is queried with settings.search_top_k."""
        from app.core.config import settings
        service = _make_service()

        await service.search("query", top_k=None)

        service._store.query.assert_called_once()
        _, kwargs = service._store.query.call_args
        assert kwargs["top_k"] == settings.search_top_k

    @pytest.mark.asyncio
    async def test_explicit_top_k_overrides_default(self) -> None:
        """When top_k is supplied, the store is queried with that value."""
        service = _make_service()

        await service.search("query", top_k=10)

        _, kwargs = service._store.query.call_args
        assert kwargs["top_k"] == 10

    @pytest.mark.asyncio
    async def test_empty_query_raises_empty_query_error(self) -> None:
        """Blank / whitespace-only queries raise EmptyQueryError."""
        service = _make_service()

        with pytest.raises(EmptyQueryError):
            await service.search("   ")

    @pytest.mark.asyncio
    async def test_empty_store_returns_empty_results(self) -> None:
        """If the vector store has no documents, return an empty list."""
        service = _make_service(store_results=[])

        result = await service.search("query")

        assert result.results == []

    @pytest.mark.asyncio
    async def test_embedder_failure_raises_search_error(self) -> None:
        """If Embedder.embed_query raises, SearchError is propagated."""
        service = _make_service()
        service._embedder.embed_query.side_effect = RuntimeError("model OOM")

        with pytest.raises(SearchError, match="Query embedding failed"):
            await service.search("query")

    @pytest.mark.asyncio
    async def test_store_failure_raises_search_error(self) -> None:
        """If VectorStore.query raises, SearchError is propagated."""
        service = _make_service()
        service._store.query.side_effect = RuntimeError("DB timeout")

        with pytest.raises(SearchError, match="Vector store query failed"):
            await service.search("query")
