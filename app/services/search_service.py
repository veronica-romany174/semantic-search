"""
app/services/search_service.py

Stub — full implementation will be added in the search pipeline commit.
"""

from app.models.search_models import SearchResponse


class SearchService:
    """
    Orchestrates the semantic search pipeline:
        1. Embed the user query into a vector
        2. Query the vector store for the top-K nearest neighbours
        3. Return the matching chunks with their similarity scores
    """

    async def search(self, query: str) -> SearchResponse:
        """Run semantic search and return ranked results."""
        raise NotImplementedError("SearchService.search — not yet implemented")


# Module-level singleton — controllers import this instance.
search_service = SearchService()
