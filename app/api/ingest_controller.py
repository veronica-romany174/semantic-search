"""
app/api/ingest_controller.py

Handles incoming requests to POST /ingest/.

This layer is responsible only for HTTP concerns:
  - Parsing the multipart form and detecting whether the caller sent
    file bytes, multiple file bytes, or a directory path string.
  - Validating that all uploaded files are PDFs and that the caller
    did not mix file uploads with a directory path in the same request.
  - Delegating the actual processing to IngestService.
  - Translating service-level errors into appropriate HTTP responses.

Responses:
  200  Ingestion succeeded.  Body contains a human-readable message and
       the list of file names that were successfully stored.
  400  The request was rejected before processing began — for example,
       the 'input' field was missing, a non-PDF file was supplied, or
       file uploads and a directory path were combined in one request.
  500  An unexpected error occurred while processing the files — for
       example, a PDF could not be parsed or the vector store failed.
"""

from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Request, UploadFile
from starlette.datastructures import UploadFile as StarletteUploadFile
from fastapi.responses import JSONResponse

from app.core.exceptions import AppBaseException, InvalidFileTypeError
from app.core.logger import get_logger
from app.core.constants import ALLOWED_PDF_EXTENSION, ALLOWED_PDF_CONTENT_TYPE
from app.models.ingest_models import IngestResponse
from app.services.ingest_service import ingest_service

logger = get_logger(__name__)

router = APIRouter(prefix="/ingest", tags=["Ingest"])

# ── Helpers ────────────────────────────────────────────────────────────────────

def _is_valid_pdf(file: UploadFile) -> bool:
    """
    Return True when the upload passes the PDF guard.

    Rule: filename extension MUST be .pdf (case-insensitive).
          If the client also supplies a content-type it must be application/pdf.
    """
    extension_ok = Path(file.filename or "").suffix.lower() == ALLOWED_PDF_EXTENSION
    if not extension_ok:
        return False
    if file.content_type and file.content_type != ALLOWED_PDF_CONTENT_TYPE:
        return False
    return True


def _err(message: str, status: int = 400) -> JSONResponse:
    """Return a JSON error response matching the swagger error schema."""
    return JSONResponse(status_code=status, content={"error": message})


# ── Endpoint ───────────────────────────────────────────────────────────────────

@router.post("/", response_model=IngestResponse, summary="Ingest PDFs into the system")
async def ingest(request: Request) -> JSONResponse:
    """
    Accept one of:
      • A single PDF upload  → -F "input=@file.pdf"
      • Multiple PDF uploads → -F "input=@a.pdf" -F "input=@b.pdf"
      • A directory path     → -F "input=/data/pdfs"

    Only PDF files are accepted for file uploads.
    """
    # ── 1. Parse multipart form ────────────────────────────────────────────────
    try:
        form = await request.form()
    except Exception:
        return _err("Invalid multipart/form-data payload.")

    # ── 2. Require the 'input' field ───────────────────────────────────────────
    if "input" not in form:
        return _err("'input' field is required.")

    # ── 3. Separate uploads from a directory string ────────────────────────────
    # Use form._list internally to reliably get all values for 'input'.
    uploaded_files: List[UploadFile] = []
    directory_path: Optional[str] = None

    for key, value in form._list:  # type: ignore[attr-defined]
        if key != "input":
            continue
        if isinstance(value, StarletteUploadFile):
            uploaded_files.append(value)
        elif isinstance(value, str):
            stripped = value.strip()
            if stripped:
                directory_path = stripped

    # ── 4. Validate: must supply one mode, not both ────────────────────────────
    if not uploaded_files and not directory_path:
        return _err("'input' field is required.")

    if uploaded_files and directory_path:
        return _err("Provide either file(s) or a directory path, not both.")

    # ── 5. Validate PDF files ──────────────────────────────────────────────────
    if uploaded_files:
        for file in uploaded_files:
            if not _is_valid_pdf(file):
                return _err(
                    f"Only PDF files are accepted. '{file.filename}' is not a PDF."
                )

    # ── 6. Delegate to service ─────────────────────────────────────────────────
    logger.info(
        "Ingest request received — %s",
        f"{len(uploaded_files)} file(s)" if uploaded_files else f"directory: {directory_path}",
    )

    try:
        if uploaded_files:
            result: IngestResponse = await ingest_service.ingest_files(uploaded_files)
        else:
            result = await ingest_service.ingest_directory(directory_path)  # type: ignore[arg-type]

    except InvalidFileTypeError as exc:
        logger.warning("Invalid file type rejected by service: %s", exc)
        return _err(str(exc))

    except AppBaseException as exc:
        logger.exception("Ingest pipeline error: %s", exc)
        return _err("Failed to process uploaded file.", status=500)

    except NotImplementedError as exc:
        logger.error("Service not yet implemented: %s", exc)
        return _err("Ingest service is not yet implemented.", status=500)

    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected error during ingest: %s", exc)
        return _err("Failed to process uploaded file.", status=500)

    logger.info("Ingest complete — %d file(s) stored.", len(result.files))
    return JSONResponse(status_code=200, content=result.model_dump())
