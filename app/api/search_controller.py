"""
app/api/search_controller.py

Handles incoming requests to POST /search/.

This layer is responsible only for HTTP concerns:
  - Parsing and validating the JSON request body, ensuring the query
    field is present and not empty.
  - Delegating the semantic search to SearchService.
  - Translating service-level errors into appropriate HTTP responses.

Responses:
  200  Search completed successfully.  Body contains a list of results,
       each with the source document name, a relevance score between 0
       and 1, and the matching text chunk.  An empty list means no
       documents have been ingested yet or nothing matched the query.
  400  The request was malformed — for example, the query field was
       missing or contained only whitespace.
  500  An unexpected error occurred while performing the search.
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.core.exceptions import AppBaseException, EmptyQueryError, SearchError
from app.core.logger import get_logger
from app.models.search_models import SearchRequest, SearchResponse
from app.services.search_service import search_service

logger = get_logger(__name__)

router = APIRouter(prefix="/search", tags=["Search"])


# ── Helpers ────────────────────────────────────────────────────────────────────

def _err(message: str, status: int = 400) -> JSONResponse:
    """Return a JSON error response with the standard error shape."""
    return JSONResponse(status_code=status, content={"error": message})


# ── Endpoint ───────────────────────────────────────────────────────────────────

@router.post("/", response_model=SearchResponse, summary="Perform semantic search")
async def search(body: SearchRequest) -> JSONResponse:
    """
    Accepts a JSON body with the following fields:

      query   (required) — the natural-language question or phrase to search for.
      top_k   (optional) — how many results to return.  Must be between 1 and 100.
                           Defaults to the value of SEARCH_TOP_K in settings
                           (5 unless overridden via environment variable).

    Returns a ranked list of the most semantically similar text chunks found
    across all ingested documents, ordered from most to least relevant.
    Each result includes the source document name, a relevance score, and
    the matching text excerpt.
    """
    
    query = body.query

    logger.info("Search request received — query: '%s'", query[:120])

    # ── Delegate to service ────────────────────────────────────────────────────
    try:
        result: SearchResponse = await search_service.search(query, top_k=body.top_k)

    except EmptyQueryError as exc:
        logger.warning("Empty query rejected by service: %s", exc)
        return _err(str(exc))

    except SearchError as exc:
        logger.exception("Search pipeline error: %s", exc)
        return _err("Search processing failed.", status=500)

    except AppBaseException as exc:
        logger.exception("Application error during search: %s", exc)
        return _err("Search processing failed.", status=500)

    except NotImplementedError as exc:
        logger.error("Service not yet implemented: %s", exc)
        return _err("Search service is not yet implemented.", status=500)

    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected error during search: %s", exc)
        return _err("Search processing failed.", status=500)

    logger.info("Search complete — %d result(s) returned.", len(result.results))
    return JSONResponse(status_code=200, content=result.model_dump())
