"""
app/vector_store/chroma_store.py

ChromaDB implementation of the VectorStore interface.

Uses a persistent on-disk client so vectors survive restarts.
All backend-specific details are fully contained here — the rest of the
application never imports from `chromadb` directly.
"""

from __future__ import annotations

from typing import List

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.config import settings
from app.core.exceptions import VectorStoreError
from app.core.logger import get_logger
from app.vector_store.base import StoreResult, TextChunk, VectorStore

logger = get_logger(__name__)


class ChromaVectorStore(VectorStore):
    """
    VectorStore backed by a local ChromaDB persistent collection.

    The client and collection are initialised once on construction and
    reused for the lifetime of the object — safe for a singleton pattern
    used by IngestService and SearchService.
    """

    def __init__(
        self,
        persist_dir: str | None = None,
        collection_name: str | None = None,
    ) -> None:
        """
        Args:
            persist_dir     : Directory where ChromaDB writes its SQLite files.
                              Defaults to ``settings.chroma_persist_dir``.
            collection_name : Name of the ChromaDB collection.
                              Defaults to ``settings.chroma_collection``.
        """
        self._persist_dir = persist_dir or settings.chroma_persist_dir
        self._collection_name = collection_name or settings.chroma_collection

        logger.info(
            "Initialising ChromaVectorStore — persist_dir=%s  collection=%s",
            self._persist_dir,
            self._collection_name,
        )

        try:
            self._client = chromadb.PersistentClient(
                path=self._persist_dir,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            self._collection = self._client.get_or_create_collection(
                name=self._collection_name,
                # cosine distance keeps similarity scores in [-1, 1];
                # we negate them on the way out so higher = better.
                metadata={"hnsw:space": "cosine"},
            )
        except Exception as exc:
            raise VectorStoreError(
                f"Failed to initialise ChromaDB at '{self._persist_dir}': {exc}"
            ) from exc

        logger.info(
            "ChromaVectorStore ready — %d document(s) in collection.",
            self._collection.count(),
        )

    # ── VectorStore interface ──────────────────────────────────────────────────

    def upsert(self, chunks: List[TextChunk]) -> None:
        """Add or overwrite chunks. Each chunk must have embedding populated."""
        if not chunks:
            return

        # Validate embeddings are present before hitting the backend.
        missing = [c.id for c in chunks if not c.embedding]
        if missing:
            raise VectorStoreError(
                f"Chunks missing embeddings (must embed before upsert): {missing}"
            )

        try:
            self._collection.upsert(
                ids=[c.id for c in chunks],
                embeddings=[c.embedding for c in chunks],
                documents=[c.text for c in chunks],
                metadatas=[
                    {
                        "source_file": c.source_file,
                        "page_number": c.page_number,
                        "chunk_index": c.chunk_index,
                    }
                    for c in chunks
                ],
            )
        except Exception as exc:
            raise VectorStoreError(f"upsert failed: {exc}") from exc

        logger.debug("Upserted %d chunk(s) into '%s'.", len(chunks), self._collection_name)

    def query(self, embedding: List[float], top_k: int = 5) -> List[StoreResult]:
        """Return the top_k nearest chunks to the given embedding vector."""
        if not embedding:
            raise VectorStoreError("Cannot query with an empty embedding vector.")

        try:
            raw = self._collection.query(
                query_embeddings=[embedding],
                n_results=min(top_k, self._collection.count() or 1),
                include=["documents", "metadatas", "distances"],
            )
        except Exception as exc:
            raise VectorStoreError(f"query failed: {exc}") from exc

        results: List[StoreResult] = []

        # ChromaDB returns lists-of-lists (one per query); we always send one.
        docs = raw.get("documents") or [[]]
        metas = raw.get("metadatas") or [[]]
        distances = raw.get("distances") or [[]]

        for doc, meta, dist in zip(docs[0], metas[0], distances[0]):
            # Cosine distance ∈ [0, 2]; convert to similarity ∈ [-1, 1].
            similarity = 1.0 - dist
            results.append(
                StoreResult(
                    text=doc,
                    source_file=meta.get("source_file", ""),
                    page_number=int(meta.get("page_number", 0)),
                    score=round(similarity, 4),
                )
            )

        logger.debug("Query returned %d result(s).", len(results))
        return results

    def clear(self) -> None:
        """Remove all documents from the collection."""
        try:
            ids = self._collection.get(include=[])["ids"]
            if ids:
                self._collection.delete(ids=ids)
                logger.info("Cleared %d document(s) from '%s'.", len(ids), self._collection_name)
            else:
                logger.debug("clear() called on already-empty collection.")
        except Exception as exc:
            raise VectorStoreError(f"clear failed: {exc}") from exc
