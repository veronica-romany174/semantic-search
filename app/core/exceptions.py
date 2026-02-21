"""
app/core/exceptions.py

Custom exception hierarchy for the application.

Raising typed exceptions from services lets controllers catch specific
cases and return the correct HTTP status code without leaking internals.
"""


class AppBaseException(Exception):
    """Root exception — catch-all for any application-level error."""


# ── Ingest exceptions ──────────────────────────────────────────────────────────

class InvalidFileTypeError(AppBaseException):
    """Raised when a non-PDF file is submitted to the ingest endpoint."""


class FileProcessingError(AppBaseException):
    """Raised when PDF parsing or chunking fails for a given file."""


class EmbeddingError(AppBaseException):
    """Raised when the embedding model fails to produce vectors."""


# ── Vector store exceptions ────────────────────────────────────────────────────

class VectorStoreError(AppBaseException):
    """Raised when an interaction with the vector database fails."""


# ── Search exceptions ──────────────────────────────────────────────────────────

class EmptyQueryError(AppBaseException):
    """Raised when an empty or whitespace-only query is submitted."""


class SearchError(AppBaseException):
    """Raised when the semantic search operation fails."""
