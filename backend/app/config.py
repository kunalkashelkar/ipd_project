# ============================================================
# Application Configuration — Pydantic Settings
# ============================================================
# Reads values from environment variables / .env file.
# Import this module wherever you need config values.
# ============================================================

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


# Project root is two levels up from this file (backend/app/config.py → project root)
PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Central application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ────────────────────────────────────────
    app_name: str = "hybrid-xai-vuln-detection"
    app_env: str = "development"
    app_debug: bool = True
    app_log_level: str = "DEBUG"
    app_secret_key: str = "change-me"

    # ── Backend Server ─────────────────────────────────────
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    backend_workers: int = 1
    backend_reload: bool = True
    cors_origins: str = "http://localhost:5173"

    # ── Database ───────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/xai_vuln_db"
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_echo_sql: bool = False

    # ── File Storage ───────────────────────────────────────
    upload_dir: str = "./uploads"
    max_upload_size_mb: int = 50
    allowed_extensions: str = ".c,.cpp,.h,.hpp,.zip"

    # ── Logging ────────────────────────────────────────────
    log_dir: str = "./logs"

    # ── Joern / Parser ─────────────────────────────────────
    joern_home: str = "/opt/joern"
    joern_timeout: int = 300
    graph_output_dir: str = "./graphs"

    # ── Computed helpers ───────────────────────────────────
    @property
    def cors_origin_list(self) -> list[str]:
        """Parse CORS_ORIGINS comma-separated string into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def allowed_extension_list(self) -> list[str]:
        """Parse ALLOWED_EXTENSIONS comma-separated string into a list."""
        return [ext.strip().lower() for ext in self.allowed_extensions.split(",")]

    @property
    def max_upload_size_bytes(self) -> int:
        """Convert MB limit to bytes."""
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def upload_path(self) -> Path:
        """Resolved upload directory path."""
        p = Path(self.upload_dir)
        if not p.is_absolute():
            p = PROJECT_ROOT / p
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def log_path(self) -> Path:
        """Resolved log directory path."""
        p = Path(self.log_dir)
        if not p.is_absolute():
            p = PROJECT_ROOT / p
        p.mkdir(parents=True, exist_ok=True)
        return p


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (singleton pattern)."""
    return Settings()
