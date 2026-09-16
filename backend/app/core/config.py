# ============================================================
# Application Configuration — Pydantic Settings (v2)
# ============================================================
# Central settings loaded from environment variables / .env file.
# All modules import `get_settings()` to access configuration.
# ============================================================

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root is three levels up: backend/app/core/config.py → project root
PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Central application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=(str(BACKEND_ROOT / ".env"), str(PROJECT_ROOT / ".env")),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ────────────────────────────────────────
    app_name: str = "VulnScanBackend"
    app_env: str = "development"
    debug: bool = True

    # ── Backend Server ─────────────────────────────────────
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    backend_workers: int = 1
    backend_reload: bool = True

    # ── CORS ───────────────────────────────────────────────
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000"

    # ── Database ───────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/vulnscan"
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_echo_sql: bool = False

    # ── Authentication ─────────────────────────────────────
    secret_key: str = "change-this-to-a-random-secret-key"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # ── Redis ──────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── Celery ─────────────────────────────────────────────
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"
    celery_task_always_eager: bool = False

    # ── Storage ────────────────────────────────────────────
    storage_backend: str = "local"
    local_storage_path: str = "./storage"
    s3_endpoint: str | None = "http://localhost:9000"
    s3_region: str = "us-east-1"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "vulnscan"
    s3_secure: bool = False

    # ── Uploads & Archives ─────────────────────────────────
    max_upload_size_mb: int = 200
    max_extraction_size_mb: int = 500
    max_archive_files: int = 10000
    allowed_upload_extensions: str = ".zip,.jar,.java,.py,.js,.ts,.c,.cpp,.h,.hpp"

    # ── AI & Pipeline ──────────────────────────────────────
    ai_mode: str = "mock"
    model_storage_path: str = "./models"
    ai_device: str = "cpu"
    joern_home: str = "/opt/joern"
    joern_parse_timeout: int = 120
    gnn_model_path: str = "./models/gnn/checkpoints/best_model.pt"
    embedding_model_name: str = "microsoft/codebert-base"
    default_vuln_threshold: float = 0.5
    max_file_size_bytes: int = 10_000_000

    # ── Logging ────────────────────────────────────────────
    log_level: str = "DEBUG"
    log_dir: str = "./logs"

    # ── Frontend ───────────────────────────────────────────
    frontend_url: str = "http://localhost:5173"

    # ── Computed helpers ───────────────────────────────────

    @property
    def cors_origin_list(self) -> list[str]:
        """Parse CORS_ORIGINS comma-separated string into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def allowed_extension_list(self) -> list[str]:
        """Parse ALLOWED_UPLOAD_EXTENSIONS comma-separated string into a list."""
        return [ext.strip().lower() for ext in self.allowed_upload_extensions.split(",")]

    @property
    def max_upload_size_bytes(self) -> int:
        """Convert MB limit to bytes."""
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def max_extraction_size_bytes(self) -> int:
        """Convert extraction MB limit to bytes."""
        return self.max_extraction_size_mb * 1024 * 1024

    @property
    def storage_path(self) -> Path:
        """Resolved storage directory path."""
        p = Path(self.local_storage_path)
        if not p.is_absolute():
            p = PROJECT_ROOT / p
        return p

    @property
    def upload_path(self) -> Path:
        """Resolved upload directory path."""
        return self.storage_path / "uploads"

    @property
    def report_path(self) -> Path:
        """Resolved report directory path."""
        return self.storage_path / "reports"

    @property
    def log_path(self) -> Path:
        """Resolved log directory path."""
        p = Path(self.log_dir)
        if not p.is_absolute():
            p = PROJECT_ROOT / p
        return p

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    # Backward-compatibility aliases for legacy pipeline routers
    @property
    def app_debug(self) -> bool:
        return self.debug

    @property
    def app_log_level(self) -> str:
        return self.log_level

    @property
    def app_secret_key(self) -> str:
        return self.secret_key

    @property
    def upload_dir(self) -> str:
        return str(self.upload_path)

    @property
    def allowed_extensions(self) -> str:
        return self.allowed_upload_extensions


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (singleton pattern)."""
    return Settings()
