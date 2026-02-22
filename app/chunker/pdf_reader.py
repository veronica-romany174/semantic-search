"""
app/chunker/pdf_reader.py

Extracts plain text from PDF documents using PyMuPDF (fitz).

Responsibility: given raw PDF bytes, open the document and return a
mapping of 1-indexed page numbers to the text content of each page.
Pages with no extractable text are omitted from the result.
"""

from __future__ import annotations

from typing import Dict

import fitz  # PyMuPDF

from app.core.exceptions import FileProcessingError
from app.core.logger import get_logger

logger = get_logger(__name__)


class PDFReader:
    """
    Extracts plain text from a PDF given its raw bytes.

    Uses PyMuPDF (fitz) to open the document entirely in memory —
    no temporary files are created.
    """

    def read(self, file_bytes: bytes, filename: str = "unknown.pdf") -> Dict[int, str]:
        """
        Parse a PDF and return the text content of each non-blank page.

        Args:
            file_bytes : Raw bytes of the PDF file.
            filename   : Original filename — used only for logging and error messages.

        Returns:
            A dict mapping 1-indexed page numbers to their text content.
            Pages that contain only whitespace are omitted.

        Raises:
            FileProcessingError: If the bytes cannot be parsed as a PDF or
                                 if text extraction fails.
        """
        if not file_bytes:
            raise FileProcessingError(f"'{filename}' is empty — nothing to read.")

        try:
            # stream= opens from bytes without touching the filesystem.
            doc = fitz.open(stream=file_bytes, filetype="pdf")
        except Exception as exc:
            raise FileProcessingError(
                f"'{filename}' could not be opened as a PDF: {exc}"
            ) from exc

        total_pages = len(doc)
        pages: Dict[int, str] = {}
        try:
            for page_index in range(total_pages):
                page = doc[page_index]
                text = page.get_text("text")          # plain text, preserves line breaks
                if text.strip():                       # skip blank/image-only pages
                    pages[page_index + 1] = text       # 1-indexed page numbers
        except Exception as exc:
            raise FileProcessingError(
                f"Text extraction failed for '{filename}': {exc}"
            ) from exc
        finally:
            doc.close()

        logger.info(
            "'%s' — extracted text from %d / %d page(s).",
            filename,
            len(pages),
            total_pages,
        )

        if not pages:
            raise FileProcessingError(
                f"'{filename}' contains no extractable text "
                "(the PDF may be image-only or empty)."
            )

        return pages
