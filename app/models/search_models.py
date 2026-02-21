"""
app/models/search_models.py

Pydantic DTOs for the search flow — request body and response.
"""

from typing import List
from pydantic import BaseModel, field_validator


class SearchRequest(BaseModel):
    """
    JSON body for POST /search/.

        { "query": "Explain how vector embeddings work." }
    """

    query: str

    @field_validator("query")
    @classmethod
    def query_must_not_be_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Query cannot be empty.")
        return v.strip()


class SearchResult(BaseModel):
    """
    A single retrieved chunk from the vector store.

    Matches the swagger result item schema:
        {
            "document": "sample.pdf",
            "score": 0.89,
            "content": "Vector embeddings represent text in a numerical space..."
        }
    """

    document: str
    score: float
    content: str


class SearchResponse(BaseModel):
    """
    Successful response for POST /search/.

        { "results": [ <SearchResult>, ... ] }
    """

    results: List[SearchResult]
