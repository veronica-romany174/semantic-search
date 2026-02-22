"""
app/vector_store/base.py

Abstract interface for the vector store layer.

Design goals:
  - Services depend only on this interface, never on a concrete backend.
  - TextChunk and StoreResult are the shared vocabulary across all layers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List


# ── Shared data-transfer objects ──────────────────────────────────────────────

@dataclass
class TextChunk:
    """
    A piece of text extracted from a source document, ready to be embedded
    and stored.

    Attributes:
        text        : The actual chunk content.
        source_file : Original filename (e.g. "report.pdf").
        page_number : 1-indexed page the chunk came from (0 if unknown).
        chunk_index : Position of this chunk within the document (0-indexed).
        embedding   : Vector representation — populated by the Embedder,
                      empty until embedding is run.
    """

    text: str
    source_file: str
    page_number: int
    chunk_index: int
    embedding: List[float] = field(default_factory=list)

    @property
    def id(self) -> str:
        """Stable, unique identifier for this chunk used as the Chroma document id."""
        return f"{self.source_file}__p{self.page_number}__c{self.chunk_index}"


@dataclass
class StoreResult:
    """
    A single result returned from a vector similarity search.

    Attributes:
        text        : The chunk content.
        source_file : Document the chunk came from.
        page_number : Page within that document.
        score       : Similarity score (higher = more similar; range depends on backend).
    """

    text: str
    source_file: str
    page_number: int
    score: float


# ── Abstract base ──────────────────────────────────────────────────────────────

class VectorStore(ABC):
    """
    Contract every vector-store backend must fulfil.

    Concrete implementations (e.g. ChromaVectorStore) wrap a specific backend
    and translate its API to this interface.
    """

    @abstractmethod
    def upsert(self, chunks: List[TextChunk]) -> None:
        """
        Add or overwrite chunks in the store.

        Each chunk must have its `embedding` field populated before calling.
        Chunks are identified by `chunk.id`; re-upserting the same id
        overwrites the previous entry (idempotent).

        Args:
            chunks: Embedded TextChunk objects to persist.

        Raises:
            VectorStoreError: If the backend operation fails.
        """

    @abstractmethod
    def query(self, embedding: List[float], top_k: int = 5) -> List[StoreResult]:
        """
        Return the `top_k` most similar chunks to the given embedding.

        Args:
            embedding : Query vector (must match the stored embedding dimension).
            top_k     : Maximum number of results to return.

        Returns:
            List of StoreResult sorted by descending similarity.

        Raises:
            VectorStoreError: If the backend operation fails.
        """

    @abstractmethod
    def clear(self) -> None:
        """
        Remove all documents from the collection.

        Useful for tests and admin operations. The collection itself is kept.

        Raises:
            VectorStoreError: If the backend operation fails.
        """
