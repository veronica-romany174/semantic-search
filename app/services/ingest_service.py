"""
app/services/ingest_service.py

Orchestrates the full PDF ingest pipeline:

    UploadFile / path
      └─ PDFReader.read()         bytes → {page_num: text}
           └─ TextChunker.chunk() → [TextChunk]
                └─ Embedder.embed_texts() → [[float]]
                     └─ VectorStore.upsert()

All four dependencies are constructor-injected so tests can swap
them out with mocks; the module-level singleton wires in the real
production implementations.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import List

from fastapi import UploadFile

from app.chunker.pdf_reader import PDFReader
from app.chunker.text_chunker import TextChunker
from app.core.exceptions import FileProcessingError
from app.core.logger import get_logger
from app.embedder.base import Embedder
from app.embedder.sentence_transformer_embedder import SentenceTransformerEmbedder
from app.models.ingest_models import IngestResponse
from app.vector_store.base import VectorStore
from app.vector_store.chroma_store import ChromaVectorStore

logger = get_logger(__name__)


class IngestService:
    """
    Orchestrates the full ingest pipeline for one or more PDF files.

    Design choices:
    - **Partial success**: if one file in a batch fails it is skipped
      and logged; the remaining files are still processed. The response
      lists only files that were successfully stored.
    - **Constructor injection**: all heavy dependencies are passed in,
      making the service easy to unit-test with lightweight mocks.
    """

    def __init__(
        self,
        reader: PDFReader | None = None,
        chunker: TextChunker | None = None,
        embedder: Embedder | None = None,
        store: VectorStore | None = None,
    ) -> None:
        self._reader: PDFReader = reader or PDFReader()
        self._chunker: TextChunker = chunker or TextChunker()
        self._embedder: Embedder = embedder or SentenceTransformerEmbedder()
        self._store: VectorStore = store or ChromaVectorStore()

    # ── Public API ─────────────────────────────────────────────────────────────

    async def ingest_files(self, files: List[UploadFile]) -> IngestResponse:
        """
        Ingest one or more uploaded PDF files.

        Each file is processed independently — a failure in one does
        not abort the remaining files (partial-success semantics).

        Args:
            files: FastAPI UploadFile objects from the multipart form.

        Returns:
            IngestResponse listing the filenames that were stored.
        """
        if not files:
            return IngestResponse(
                message="No files provided.",
                files=[],
            )

        stored: List[str] = []

        for upload in files:
            filename = upload.filename or "unknown.pdf"
            try:
                raw = await upload.read()
                chunks_stored = self._process_file(raw, filename)
                stored.append(filename)
                logger.info("'%s' — ingested %d chunk(s).", filename, chunks_stored)
            except FileProcessingError as exc:
                logger.warning("Skipping '%s' — %s", filename, exc)
            except Exception as exc:  # noqa: BLE001
                logger.exception("Unexpected error ingesting '%s': %s", filename, exc)

        n = len(stored)
        return IngestResponse(
            message=f"Successfully ingested {n} PDF document(s)." if n else "No files could be processed.",
            files=stored,
        )

    async def ingest_directory(self, path: str) -> IngestResponse:
        """
        Ingest all PDF files found directly under the given directory.

        Args:
            path: Absolute or relative filesystem path to a directory.

        Returns:
            IngestResponse listing the filenames that were stored.

        Raises:
            FileProcessingError: If the path does not exist or is not a directory.
        """
        dir_path = Path(path)

        if not dir_path.exists():
            raise FileProcessingError(f"Directory not found: '{path}'")
        if not dir_path.is_dir():
            raise FileProcessingError(f"Path is not a directory: '{path}'")

        pdf_files = sorted(dir_path.glob("*.pdf"))

        if not pdf_files:
            logger.info("No PDF files found in '%s'.", path)
            return IngestResponse(
                message=f"No PDF files found in '{path}'.",
                files=[],
            )

        stored: List[str] = []

        for pdf_path in pdf_files:
            filename = pdf_path.name
            try:
                raw = pdf_path.read_bytes()
                chunks_stored = self._process_file(raw, filename)
                stored.append(filename)
                logger.info("'%s' — ingested %d chunk(s).", filename, chunks_stored)
            except FileProcessingError as exc:
                logger.warning("Skipping '%s' — %s", filename, exc)
            except Exception as exc:  # noqa: BLE001
                logger.exception("Unexpected error ingesting '%s': %s", filename, exc)

        n = len(stored)
        return IngestResponse(
            message=f"Successfully ingested {n} PDF document(s)." if n else "No files could be processed.",
            files=stored,
        )

    # ── Internals ──────────────────────────────────────────────────────────────

    def _process_file(self, file_bytes: bytes, filename: str) -> int:
        """
        Run the full pipeline for a single PDF.

        Steps:
            1. PDFReader.read()          → {page_num: text}
            2. TextChunker.chunk()       → [TextChunk]   (embedding=[])
            3. Embedder.embed_texts()    → [[float]]
            4. Attach embeddings to chunks
            5. VectorStore.upsert()      → chunks stored

        Args:
            file_bytes : Raw bytes of the PDF.
            filename   : Original filename — used for metadata and logging.

        Returns:
            Number of chunks stored in the vector database.

        Raises:
            FileProcessingError: Propagated from PDFReader on parse failure.
            EmbeddingError:      Propagated from Embedder on model failure.
            VectorStoreError:    Propagated from VectorStore on DB failure.
        """
        # 1 & 2 — read + chunk
        pages = self._reader.read(file_bytes, filename)
        chunks = self._chunker.chunk(pages, source_file=filename)

        if not chunks:
            logger.warning("'%s' produced no chunks — skipping upsert.", filename)
            return 0

        # 3 — embed all chunk texts in one batch call
        texts = [c.text for c in chunks]
        vectors = self._embedder.embed_texts(texts)

        # 4 — attach embeddings to chunk objects
        for chunk, vector in zip(chunks, vectors):
            chunk.embedding = vector

        # 5 — upsert into the vector store
        self._store.upsert(chunks)
        return len(chunks)


# ── Module-level singleton ─────────────────────────────────────────────────────
# Controllers import this instance.  Tests construct IngestService directly
# with injected mocks.

ingest_service = IngestService()
