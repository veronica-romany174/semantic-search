"""
tests/services/test_ingest_service.py

Unit tests for IngestService.

All four dependencies (PDFReader, TextChunker, Embedder, VectorStore)
are replaced with lightweight MagicMock / AsyncMock objects so these
tests are fast, deterministic, and have zero external I/O.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import FileProcessingError
from app.models.ingest_models import IngestResponse
from app.services.ingest_service import IngestService
from app.vector_store.base import TextChunk


# ── Fixtures & helpers ─────────────────────────────────────────────────────────

def _make_chunk(text: str, filename: str = "doc.pdf", page: int = 1, idx: int = 0) -> TextChunk:
    return TextChunk(text=text, source_file=filename, page_number=page, chunk_index=idx)


def _fake_upload(filename: str, content: bytes = b"fake-pdf") -> MagicMock:
    """Create a minimal mock of fastapi.UploadFile."""
    upload = MagicMock()
    upload.filename = filename
    # read() is a coroutine in the real UploadFile
    upload.read = AsyncMock(return_value=content)
    return upload


def _make_service(
    pages: dict | None = None,
    chunks: list[TextChunk] | None = None,
    vectors: list[list[float]] | None = None,
) -> IngestService:
    """
    Build an IngestService with all four dependencies mocked.
    Default values define a simple happy-path scenario.
    """
    pages = pages if pages is not None else {1: "Some page text."}
    chunks = chunks if chunks is not None else [
        _make_chunk("chunk A"), _make_chunk("chunk B"), _make_chunk("chunk C")
    ]
    vectors = vectors if vectors is not None else [[0.1] * 384 for _ in chunks]

    reader = MagicMock()
    reader.read.return_value = pages

    chunker = MagicMock()
    chunker.chunk.return_value = chunks

    embedder = MagicMock()
    embedder.embed_texts.return_value = vectors

    store = MagicMock()
    store.upsert.return_value = None   # upsert() returns None

    return IngestService(reader=reader, chunker=chunker, embedder=embedder, store=store)


# ── ingest_files tests ─────────────────────────────────────────────────────────

class TestIngestFiles:

    @pytest.mark.asyncio
    async def test_happy_path_single_file(self) -> None:
        """A valid file → IngestResponse with its name in .files."""
        service = _make_service()
        upload = _fake_upload("report.pdf")

        result = await service.ingest_files([upload])

        assert isinstance(result, IngestResponse)
        assert result.files == ["report.pdf"]
        assert "1" in result.message

    @pytest.mark.asyncio
    async def test_happy_path_multiple_files(self) -> None:
        """Two valid files → both appear in .files."""
        service = _make_service()
        uploads = [_fake_upload("a.pdf"), _fake_upload("b.pdf")]

        result = await service.ingest_files(uploads)

        assert result.files == ["a.pdf", "b.pdf"]

    @pytest.mark.asyncio
    async def test_empty_file_list(self) -> None:
        """Empty list → IngestResponse with files=[] and no errors."""
        service = _make_service()

        result = await service.ingest_files([])

        assert result.files == []

    @pytest.mark.asyncio
    async def test_partial_failure_bad_file_is_skipped(self) -> None:
        """
        If one file raises FileProcessingError the others still succeed.
        The failed file must NOT appear in the result.
        """
        service = _make_service()

        # First call raises, second call succeeds
        service._reader.read.side_effect = [
            FileProcessingError("corrupt PDF"),
            {1: "Good page text."},
        ]

        result = await service.ingest_files([_fake_upload("bad.pdf"), _fake_upload("good.pdf")])

        assert "bad.pdf" not in result.files
        assert "good.pdf" in result.files

    @pytest.mark.asyncio
    async def test_embedder_called_with_chunk_texts(self) -> None:
        """embed_texts must receive exactly the texts from the chunks."""
        service = _make_service()

        await service.ingest_files([_fake_upload("doc.pdf")])

        expected_texts = [c.text for c in service._chunker.chunk.return_value]
        service._embedder.embed_texts.assert_called_once_with(expected_texts)

    @pytest.mark.asyncio
    async def test_embeddings_attached_before_upsert(self) -> None:
        """
        Chunks must have their embedding field set before VectorStore.upsert
        is called — verifies the attachment step is not skipped.
        """
        chunks = [_make_chunk("hello")]
        vector = [0.5] * 384
        service = _make_service(chunks=chunks, vectors=[vector])

        await service.ingest_files([_fake_upload("doc.pdf")])

        # After the call the chunk object should have the embedding attached
        assert chunks[0].embedding == vector

    @pytest.mark.asyncio
    async def test_upsert_called_once_per_file(self) -> None:
        """VectorStore.upsert must be called exactly once per processed file."""
        service = _make_service()

        await service.ingest_files([_fake_upload("a.pdf"), _fake_upload("b.pdf")])

        assert service._store.upsert.call_count == 2

    @pytest.mark.asyncio
    async def test_returns_ingest_response_type(self) -> None:
        service = _make_service()
        result = await service.ingest_files([_fake_upload("x.pdf")])
        assert isinstance(result, IngestResponse)


# ── ingest_directory tests ─────────────────────────────────────────────────────

class TestIngestDirectory:

    @pytest.mark.asyncio
    async def test_happy_path(self, tmp_path: Path) -> None:
        """PDFs found in directory are processed; filenames in result."""
        # Create real (but minimal) dummy PDF files so glob finds them
        (tmp_path / "a.pdf").write_bytes(b"dummy")
        (tmp_path / "b.pdf").write_bytes(b"dummy")

        service = _make_service()

        result = await service.ingest_directory(str(tmp_path))

        assert sorted(result.files) == ["a.pdf", "b.pdf"]

    @pytest.mark.asyncio
    async def test_empty_directory(self, tmp_path: Path) -> None:
        """Directory with no PDFs returns empty file list."""
        service = _make_service()

        result = await service.ingest_directory(str(tmp_path))

        assert result.files == []

    @pytest.mark.asyncio
    async def test_missing_path_raises_file_processing_error(self) -> None:
        """`ingest_directory` on a non-existent path must raise FileProcessingError."""
        service = _make_service()

        with pytest.raises(FileProcessingError, match="not found"):
            await service.ingest_directory("/this/path/does/not/exist")

    @pytest.mark.asyncio
    async def test_non_directory_path_raises_file_processing_error(
        self, tmp_path: Path
    ) -> None:
        """Passing a file path (not a dir) must raise FileProcessingError."""
        some_file = tmp_path / "file.pdf"
        some_file.write_bytes(b"data")
        service = _make_service()

        with pytest.raises(FileProcessingError, match="not a directory"):
            await service.ingest_directory(str(some_file))

    @pytest.mark.asyncio
    async def test_non_pdf_files_are_ignored(self, tmp_path: Path) -> None:
        """Only *.pdf files should be picked up — .txt and others must be ignored."""
        (tmp_path / "notes.txt").write_text("ignore me")
        (tmp_path / "image.png").write_bytes(b"")
        (tmp_path / "real.pdf").write_bytes(b"dummy")

        service = _make_service()

        result = await service.ingest_directory(str(tmp_path))

        assert result.files == ["real.pdf"]
