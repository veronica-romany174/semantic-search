"""
app/main.py

FastAPI application entry point.

Responsibilities:
  - Create the FastAPI app with metadata from config
  - Register all API routers
  - Add a global exception handler for uncaught AppBaseException
  - Expose a /health endpoint for liveness probes
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.ingest_controller import router as ingest_router
from app.api.search_controller import router as search_router
from app.core.config import settings
from app.core.exceptions import AppBaseException
from app.core.logger import get_logger

logger = get_logger(__name__)

# ── App instance ───────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Ingests PDF documents, generates embeddings, and enables "
        "semantic search over the ingested content."
    ),
)

# ── Routers ────────────────────────────────────────────────────────────────────

app.include_router(ingest_router)
app.include_router(search_router)

# ── Global exception handler ───────────────────────────────────────────────────

@app.exception_handler(AppBaseException)
async def app_exception_handler(request: Request, exc: AppBaseException) -> JSONResponse:
    """
    Safety-net for any AppBaseException that escapes controller-level handling.
    Returns the swagger error shape: { "error": "..." }
    """
    logger.exception("Unhandled application error on %s: %s", request.url.path, exc)
    return JSONResponse(status_code=500, content={"error": str(exc)})


# ── Health endpoint ────────────────────────────────────────────────────────────

@app.get("/health", tags=["Health"], summary="Liveness probe")
async def health() -> dict:
    """Returns 200 OK when the service is running."""
    return {"status": "ok", "version": settings.app_version}

