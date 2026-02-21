"""
app/api/ingest_controller.py

HTTP layer for POST /ingest/.

Responsibilities (HTTP concerns only):
  - Parse multipart/form-data and detect whether input is file(s) or a path
  - Validate: field present, only PDF files accepted, no mixing of modes
  - Delegate to IngestService
  - Map service exceptions to the correct HTTP status codes

Response shapes match the swagger spec exactly:
  200 → { "message": "...", "files": [...] }
  400 → { "error": "..." }
  500 → { "error": "..." }
"""

from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Request, UploadFile
from fastapi.responses import JSONResponse

from app.core.exceptions import AppBaseException, InvalidFileTypeError
from app.core.logger import get_logger
from app.models.ingest_models import IngestResponse
from app.services.ingest_service import ingest_service

logger = get_logger(__name__)

router = APIRouter(prefix="/ingest", tags=["Ingest"])

# ── Constants ──────────────────────────────────────────────────────────────────

_ALLOWED_EXTENSION = ".pdf"
_ALLOWED_CONTENT_TYPE = "application/pdf"


# ── Helpers ────────────────────────────────────────────────────────────────────

def _is_valid_pdf(file: UploadFile) -> bool:
    """
    Return True when the upload passes the PDF guard.

    Rule: filename extension MUST be .pdf (case-insensitive).
          If the client also supplies a content-type it must be application/pdf.
    """
    extension_ok = Path(file.filename or "").suffix.lower() == _ALLOWED_EXTENSION
    if not extension_ok:
        return False
    # content_type may be absent / empty — only fail if explicitly wrong
    if file.content_type and file.content_type != _ALLOWED_CONTENT_TYPE:
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
        if isinstance(value, UploadFile):
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
