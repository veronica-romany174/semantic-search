"""
tests/conftest.py

Shared pytest fixtures available to all test modules.

Fixtures defined here are auto-discovered by pytest — no import needed.
"""

import io

import pytest
from fastapi.testclient import TestClient

from app.main import app


# ── Core client fixture ────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def client() -> TestClient:
    """
    A synchronous TestClient wrapping the FastAPI app.

    session-scoped so the app is instantiated once per test run.
    The lifespan context (startup/shutdown events) is entered automatically.
    """
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


# ── Sample file fixtures ───────────────────────────────────────────────────────

@pytest.fixture
def sample_pdf_bytes() -> bytes:
    """
    Minimal but structurally valid PDF header bytes.
    Enough for content-type / extension validation; not parseable by PyMuPDF.
    """
    return b"%PDF-1.4\n%%EOF"


@pytest.fixture
def sample_pdf_file(sample_pdf_bytes) -> tuple:
    """
    A (field_name, (filename, file_obj, content_type)) tuple ready for
    use with TestClient's `files=` parameter.

    Usage:
        response = client.post("/ingest/", files=[sample_pdf_file])
    """
    return ("input", ("sample.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf"))


@pytest.fixture
def sample_txt_file() -> tuple:
    """A non-PDF upload tuple for negative-case tests."""
    return ("input", ("readme.txt", io.BytesIO(b"hello world"), "text/plain"))
