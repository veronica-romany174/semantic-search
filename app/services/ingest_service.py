"""
app/services/ingest_service.py

Stub — full implementation will be added in the ingest pipeline commit.
The controller depends on this interface; raise NotImplementedError so
any accidental call during testing surfaces immediately.
"""

from typing import List

from fastapi import UploadFile

from app.models.ingest_models import IngestResponse


class IngestService:
    """
    Orchestrates the full ingest pipeline:
        1. Chunk  — extract text from each PDF and split into chunks
        2. Embed  — generate a vector for every chunk
        3. Store  — upsert chunks + vectors into the vector database
    """

    async def ingest_files(self, files: List[UploadFile]) -> IngestResponse:
        """Ingest one or more uploaded PDF files."""
        raise NotImplementedError("IngestService.ingest_files — not yet implemented")

    async def ingest_directory(self, path: str) -> IngestResponse:
        """Ingest all PDF files found under the given directory path."""
        raise NotImplementedError("IngestService.ingest_directory — not yet implemented")


# Module-level singleton — controllers import this instance.
ingest_service = IngestService()
