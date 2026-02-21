"""
app/models/ingest_models.py

Pydantic DTOs for the ingest flow.
The request has no DTO — FastAPI handles multipart/form-data natively
in the controller; only the response shape is defined here.
"""

from typing import List
from pydantic import BaseModel


class IngestResponse(BaseModel):
    """
    Successful response for POST /ingest/.

    Matches the swagger 200 schema:
        {
            "message": "Successfully ingested 3 PDF documents.",
            "files": ["sample.pdf"]
        }
    """

    message: str
    files: List[str]
