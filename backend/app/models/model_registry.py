# ============================================================
# Model Version Registry Model (Phase 6)
# ============================================================
# Authoritative registry of AI inference, explanation, and
# remediation models with checksums, runtime, and schema tracking.
# ============================================================

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ModelVersion(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Registered AI model version preserving immutable provenance."""

    __tablename__ = "model_versions"

    model_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    artifact_uri: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)  # SHA-256
    runtime: Mapped[str] = mapped_column(String(50), nullable=False, default="mock")  # pytorch, onnx, api, mock
    input_schema_version: Mapped[str] = mapped_column(String(50), nullable=False, default="v1.0.0")
    output_schema_version: Mapped[str] = mapped_column(String(50), nullable=False, default="v1.0.0")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="inactive", index=True)  # active, inactive, deprecated, unavailable
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
