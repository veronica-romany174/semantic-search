"""
app/core/logger.py

Centralised logging configuration.
Every module should obtain its logger via:

    from app.core.logger import get_logger
    logger = get_logger(__name__)
"""

import logging
import sys
from app.core.config import settings


def _build_handler() -> logging.StreamHandler:
    """Return a stdout handler with a structured, readable format."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG if settings.debug else logging.INFO)

    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(fmt)
    return handler


def _configure_root_logger() -> None:
    """Configure the root logger once at import time."""
    root = logging.getLogger()
    if root.handlers:
        # Already configured (e.g. by a test framework) — leave it alone.
        return

    root.setLevel(logging.DEBUG if settings.debug else logging.INFO)
    root.addHandler(_build_handler())

    # Silence noisy third-party loggers.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


_configure_root_logger()


def get_logger(name: str) -> logging.Logger:
    """
    Return a named logger.

    Usage
    -----
    >>> logger = get_logger(__name__)
    >>> logger.info("Service started")
    """
    return logging.getLogger(name)
