"""
app/services/search_service.py

Orchestrates the semantic search pipeline:

    query string
      └─ Embedder.embed_query()   → [float]   (single vector)
           └─ VectorStore.query() → [StoreResult]
                └─ Map → SearchResponse

Same constructor-injection pattern as IngestService.
"""

from __future__ import annotations

from typing import List, Optional

from app.core.config import settings
from app.core.exceptions import EmptyQueryError, SearchError
from app.core.logger import get_logger
from app.embedder.base import Embedder
from app.embedder.sentence_transformer_embedder import SentenceTransformerEmbedder
from app.models.search_models import SearchResponse, SearchResult
from app.vector_store.base import VectorStore
from app.vector_store.chroma_store import ChromaVectorStore

logger = get_logger(__name__)


class SearchService:
    """
    Orchestrates the semantic search pipeline:
        1. Validate and normalise the query string
        2. Embed the query into a vector (reuses the already-loaded model)
        3. Query the vector store for the top-K nearest neighbours
        4. Map results to SearchResponse

    ``top_k`` can be provided per-call (from the request body) or falls back
    to ``settings.search_top_k`` (configurable via the ``SEARCH_TOP_K`` env var).
    """

    def __init__(
        self,
        embedder: Embedder | None = None,
        store: VectorStore | None = None,
    ) -> None:
        self._embedder: Embedder = embedder or SentenceTransformerEmbedder()
        self._store: VectorStore = store or ChromaVectorStore()

    # ── Public API ─────────────────────────────────────────────────────────────

    async def search(
        self,
        query: str,
        top_k: Optional[int] = None,
    ) -> SearchResponse:
        """
        Run semantic search and return ranked results.

        Args:
            query : The user's natural-language query. Must not be blank.
            top_k : Max results to return. Defaults to ``settings.search_top_k``.

        Returns:
            SearchResponse with a (possibly empty) list of SearchResult items.

        Raises:
            EmptyQueryError : The query string was blank.
            SearchError     : The embedding or vector store step failed.
        """
        # ── 1. Validate ────────────────────────────────────────────────────────
        clean_query = query.strip()
        if not clean_query:
            raise EmptyQueryError("Query must not be empty.")

        k = top_k if top_k is not None else settings.search_top_k
        logger.debug("Searching — query: '%s', top_k: %d", clean_query[:120], k)

        # ── 2. Embed query ─────────────────────────────────────────────────────
        try:
            vector = self._embedder.embed_query(clean_query)
        except Exception as exc:
            raise SearchError(f"Query embedding failed: {exc}") from exc

        # ── 3. Query vector store ──────────────────────────────────────────────
        try:
            store_results = self._store.query(vector, top_k=k)
        except Exception as exc:
            raise SearchError(f"Vector store query failed: {exc}") from exc

        # ── 4. Map to response schema ──────────────────────────────────────────
        results: List[SearchResult] = [
            SearchResult(
                document=r.source_file,
                score=round(r.score, 4),
                content=r.text,
            )
            for r in store_results
        ]

        logger.info(
            "Search complete — query: '%s', %d result(s) returned.",
            clean_query[:80],
            len(results),
        )
        return SearchResponse(results=results)


# ── Module-level singleton ─────────────────────────────────────────────────────
# Controllers import this instance. Tests construct SearchService directly
# with injected mocks.

search_service = SearchService()
