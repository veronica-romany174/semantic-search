"""
app/embedder/sentence_transformer_embedder.py

SentenceTransformer implementation of the Embedder interface.

The model is loaded lazily on first use so the FastAPI startup event
remains fast even on cold starts. All sentence_transformers details are
fully contained here — the rest of the application sees only Embedder.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from app.core.config import settings
from app.core.exceptions import EmbeddingError
from app.core.logger import get_logger
from app.embedder.base import Embedder

if TYPE_CHECKING:
    # Keep the heavy import out of the module-level scope so that the
    # import graph is clean even in environments where sentence_transformers
    # is not installed (e.g. during type-checking runs).
    from sentence_transformers import SentenceTransformer as _ST

logger = get_logger(__name__)


class SentenceTransformerEmbedder(Embedder):
    """
    Embedder backed by a HuggingFace sentence-transformers model.

    The model is loaded on the first call to embed_texts / embed_query
    (lazy initialisation). Subsequent calls reuse the already-loaded model.

    Default model: ``all-MiniLM-L6-v2``
      - Dimension : 384
      - Speed     : very fast (CPU-friendly)
      - Quality   : excellent for semantic search benchmarks
    """

    def __init__(self, model_name: str | None = None) -> None:
        """
        Args:
            model_name: HuggingFace model identifier.
                        Defaults to ``settings.embedding_model``.
        """
        self._model_name: str = model_name or settings.embedding_model
        self._model: Optional[_ST] = None  # loaded on first use

    # ── Lazy loader ────────────────────────────────────────────────────────────

    def _get_model(self) -> _ST:
        """Return the loaded model, initialising it on first call."""
        if self._model is None:
            logger.info("Loading embedding model '%s' …", self._model_name)
            try:
                from sentence_transformers import SentenceTransformer

                self._model = SentenceTransformer(self._model_name)
                logger.info(
                    "Model '%s' loaded — embedding dimension: %d",
                    self._model_name,
                    self._model.get_sentence_embedding_dimension(),
                )
            except Exception as exc:
                raise EmbeddingError(
                    f"Failed to load embedding model '{self._model_name}': {exc}"
                ) from exc
        return self._model

    # ── Embedder interface ─────────────────────────────────────────────────────

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Batch-encode document texts. Returns [] for empty input."""
        if not texts:
            return []

        try:
            model = self._get_model()
            vectors = model.encode(
                texts,
                batch_size=32,
                show_progress_bar=False,
                convert_to_numpy=True,
            )
            return [v.tolist() for v in vectors]
        except EmbeddingError:
            raise
        except Exception as exc:
            raise EmbeddingError(f"embed_texts failed: {exc}") from exc

    def embed_query(self, text: str) -> List[float]:
        """Encode a single query string."""
        results = self.embed_texts([text])
        return results[0]
