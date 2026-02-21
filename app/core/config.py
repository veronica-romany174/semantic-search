"""
app/core/config.py

Centralised configuration loaded from environment variables.
Use a .env file locally; Docker Compose injects these at runtime.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── Application ────────────────────────────────────────────────────────────
    app_name: str = "PDF Ingestor & Semantic Search API"
    app_version: str = "1.0.0"
    debug: bool = False

    # ── Vector store (ChromaDB) ────────────────────────────────────────────────
    chroma_persist_dir: str = "./data/chroma"
    chroma_collection: str = "documents"

    # ── Embedder ───────────────────────────────────────────────────────────────
    embedding_model: str = "all-MiniLM-L6-v2"

    # ── Chunker ────────────────────────────────────────────────────────────────
    chunk_size: int = 1000      # max characters per chunk
    chunk_overlap: int = 150    # characters shared between consecutive chunks

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


# Single shared instance — import this everywhere.
settings = Settings()
