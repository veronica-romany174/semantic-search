"""
app/api/search_controller.py

HTTP layer for POST /search/.

Responsibilities (HTTP concerns only):
  - Parse and validate the JSON request body
  - Delegate to SearchService
  - Map service exceptions to the correct HTTP status codes

Response shapes match the swagger spec exactly:
  200 → { "results": [ { "document", "score", "content" }, ... ] }
  400 → { "error": "..." }
  500 → { "error": "..." }
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
    """Return a JSON error response matching the swagger error schema."""
    return JSONResponse(status_code=status, content={"error": message})


# ── Endpoint ───────────────────────────────────────────────────────────────────

@router.post("/", response_model=SearchResponse, summary="Perform semantic search")
async def search(body: SearchRequest) -> JSONResponse:
    """
    Accepts a JSON body:
        { "query": "Explain how vector embeddings work." }

    Returns the top-K semantically similar chunks from the ingested documents.
    """
    # Pydantic already validated and stripped the query via SearchRequest's
    # field_validator. If the query was blank, FastAPI returns 422 automatically.
    # We raise an explicit 400 here to match the swagger error shape exactly.
    query = body.query

    logger.info("Search request received — query: '%s'", query[:120])

    # ── Delegate to service ────────────────────────────────────────────────────
    try:
        result: SearchResponse = await search_service.search(query)

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
