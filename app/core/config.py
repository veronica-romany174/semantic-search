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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


# Single shared instance — import this everywhere.
settings = Settings()
