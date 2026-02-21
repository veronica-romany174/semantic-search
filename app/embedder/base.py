"""
app/embedder/base.py

Abstract interface for the embedding layer.

Design goals:
  - Services depend only on this interface, never on sentence_transformers.
  - Two distinct methods (embed_texts vs embed_query) make the abstraction
    correct for providers that use different instruction prefixes for
    documents vs queries (e.g. Instructor, Cohere, E5).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List


class Embedder(ABC):
    """
    Contract every embedding backend must fulfil.

    Batch-encoding (embed_texts) is the primary path for ingestion.
    Query-encoding (embed_query) is the primary path for search.
    """

    @abstractmethod
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Encode a list of document-side texts into embedding vectors.

        Args:
            texts: Strings to embed. May be empty — implementations must
                   handle that case by returning an empty list.

        Returns:
            A list of float vectors, one per input text, in the same order.

        Raises:
            EmbeddingError: If the model fails to produce embeddings.
        """

    @abstractmethod
    def embed_query(self, text: str) -> List[float]:
        """
        Encode a single query string into an embedding vector.

        Args:
            text: The search query to embed.

        Returns:
            A single float vector.

        Raises:
            EmbeddingError: If the model fails to produce an embedding.
        """
