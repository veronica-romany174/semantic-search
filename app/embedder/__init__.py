"""app/embedder/__init__.py — public API of the embedder package."""

from app.embedder.base import Embedder
from app.embedder.sentence_transformer_embedder import SentenceTransformerEmbedder

__all__ = [
    "Embedder",
    "SentenceTransformerEmbedder",
]
