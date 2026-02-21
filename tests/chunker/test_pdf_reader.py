"""
tests/chunker/test_pdf_reader.py

Tests for PDFReader.

Uses a minimal, programmatically-generated PDF so the suite has no
external file dependencies. The PDF is built with PyMuPDF itself so
the same library is used to produce and consume test fixtures.
"""

import pytest
import fitz  # PyMuPDF

from app.chunker.pdf_reader import PDFReader
from app.core.exceptions import FileProcessingError


# ── Helpers ────────────────────────────────────────────────────────────────────

def make_pdf(pages: list[str]) -> bytes:
    """
    Create a minimal in-memory PDF with one text block per page.
    Returns the raw bytes suitable for passing to PDFReader.read().
    """
    doc = fitz.open()
    for text in pages:
        page = doc.new_page()
        if text.strip():  # only insert non-blank text
            page.insert_text((72, 72), text, fontsize=12)
    return doc.tobytes()


# ── Tests ──────────────────────────────────────────────────────────────────────

class TestPDFReader:

    def test_read_returns_text_per_page(self) -> None:
        """
        Each page with text must have an entry in the returned dict.
        Page numbers are 1-indexed.
        """
        pdf_bytes = make_pdf(["Hello page one.", "Hello page two."])
        reader = PDFReader()

        pages = reader.read(pdf_bytes, filename="test.pdf")

        assert len(pages) == 2
        assert 1 in pages
        assert 2 in pages
        assert "Hello page one." in pages[1]
        assert "Hello page two." in pages[2]

    def test_blank_pages_are_skipped(self) -> None:
        """
        Pages that contain only whitespace must be omitted from the result.
        """
        # Page 1: text, Page 2: blank, Page 3: text
        pdf_bytes = make_pdf(["First page text.", "", "Third page text."])
        reader = PDFReader()

        pages = reader.read(pdf_bytes, filename="sparse.pdf")

        assert 2 not in pages          # blank page skipped
        assert 1 in pages
        assert 3 in pages

    def test_page_numbers_are_one_indexed(self) -> None:
        """Keys must start at 1, not 0."""
        pdf_bytes = make_pdf(["Only page."])
        reader = PDFReader()

        pages = reader.read(pdf_bytes)

        assert 1 in pages
        assert 0 not in pages

    def test_invalid_bytes_raises_file_processing_error(self) -> None:
        """Garbage bytes must raise FileProcessingError, not a raw fitz error."""
        reader = PDFReader()

        with pytest.raises(FileProcessingError, match="could not be opened"):
            reader.read(b"this is not a pdf", filename="bad.pdf")

    def test_empty_bytes_raises_file_processing_error(self) -> None:
        """Empty bytes input must raise FileProcessingError immediately."""
        reader = PDFReader()

        with pytest.raises(FileProcessingError, match="empty"):
            reader.read(b"", filename="empty.pdf")
