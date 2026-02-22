"""
app/core/constants.py

Application-wide fixed constants.

These are business rules that are part of the system's contract and are
NOT configurable via environment variables.
"""

# ── Allowed file types ─────────────────────────────────────────────────────────

#: Only PDF files are accepted for ingestion.
ALLOWED_PDF_EXTENSION: str = ".pdf"

#: Expected MIME type for PDF uploads (content-type header).
ALLOWED_PDF_CONTENT_TYPE: str = "application/pdf"
