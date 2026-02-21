"""
tests/chunker/test_text_chunker.py

Tests for TextChunker.

Pure unit tests — no PDF parsing, no disk, no embeddings.
"""

import math

import pytest

from app.chunker.text_chunker import TextChunker
from app.vector_store.base import TextChunk


# ── Helpers ────────────────────────────────────────────────────────────────────

def chunker(size: int = 100, overlap: int = 20) -> TextChunker:
    return TextChunker(chunk_size=size, chunk_overlap=overlap)


def pages(text: str, page: int = 1) -> dict[int, str]:
    return {page: text}


# ── Tests ──────────────────────────────────────────────────────────────────────

class TestTextChunker:

    def test_empty_pages_returns_empty_list(self) -> None:
        """chunk({}) must return [] without raising."""
        result = chunker().chunk({}, source_file="doc.pdf")
        assert result == []

    def test_short_text_returns_single_chunk(self) -> None:
        """Text shorter than chunk_size must produce exactly one chunk."""
        result = chunker(size=1000, overlap=100).chunk(
            pages("Short text."), source_file="doc.pdf"
        )
        assert len(result) == 1
        assert result[0].text == "Short text."

    def test_chunk_count_matches_sliding_window_formula(self) -> None:
        """
        For a sliding window with step = size - overlap:
          number of chunks = ceil(len(text) / step)
        """
        size, overlap = 100, 20
        step = size - overlap  # 80

        # Use a length that is an exact multiple of step → clean count
        text = "x" * (5 * step)   # 400 chars → 400/80 = 5 chunks
        result = chunker(size=size, overlap=overlap).chunk(
            pages(text), source_file="doc.pdf"
        )

        assert len(result) == 5

    def test_consecutive_chunks_share_overlap(self) -> None:
        """
        The suffix of chunk[n] must equal the prefix of chunk[n+1]
        (up to `overlap` characters).
        """
        size, overlap = 20, 5
        text = "A" * 100
        result = chunker(size=size, overlap=overlap).chunk(
            pages(text), source_file="doc.pdf"
        )

        assert len(result) >= 2
        # suffix of chunk 0 == prefix of chunk 1
        suffix = result[0].text[-overlap:]
        prefix = result[1].text[:overlap]
        assert suffix == prefix

    def test_chunk_index_is_global_across_pages(self) -> None:
        """
        chunk_index must increment globally (0, 1, 2, …) across all pages,
        not reset to 0 for each page.
        """
        text = "word " * 50   # enough for multiple chunks per page
        multi_pages = {1: text, 2: text}
        result = chunker(size=50, overlap=10).chunk(multi_pages, source_file="doc.pdf")

        indices = [c.chunk_index for c in result]
        assert indices == list(range(len(indices)))

    def test_source_file_is_set_on_every_chunk(self) -> None:
        """source_file attribute must match the argument passed to chunk()."""
        result = chunker().chunk(pages("Some text for testing."), source_file="report.pdf")

        for c in result:
            assert c.source_file == "report.pdf"

    def test_page_number_is_set_correctly(self) -> None:
        """page_number in each chunk must match the page it came from."""
        result = chunker(size=50, overlap=10).chunk(
            {3: "word " * 30}, source_file="doc.pdf"
        )

        for c in result:
            assert c.page_number == 3

    def test_returns_text_chunk_objects(self) -> None:
        """All returned items must be TextChunk instances."""
        result = chunker().chunk(pages("hello world"), source_file="a.pdf")

        assert all(isinstance(c, TextChunk) for c in result)

    def test_chunks_have_empty_embedding_by_default(self) -> None:
        """
        Embedder fills embeddings later — chunker must not pre-populate them.
        """
        result = chunker().chunk(pages("hello world"), source_file="a.pdf")

        for c in result:
            assert c.embedding == []

    def test_overlap_ge_size_raises_value_error(self) -> None:
        """Misconfiguration (overlap >= size) must raise ValueError at init."""
        with pytest.raises(ValueError, match="chunk_overlap"):
            TextChunker(chunk_size=50, chunk_overlap=50)
