# ============================================================
# AI Prediction Model (Phase 5)
# ============================================================
# Persisted record of an AI model's vulnerability prediction.
# Preserves strict provenance (scan, snapshot, model, version)
# and is provider-independent.
# ============================================================

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.finding import FindingOccurrence
    from backend.app.models.scan import Scan
    from backend.app.models.source_snapshot import Function, SourceFile, SourceSnapshot


class AIPrediction(Base, UUIDPrimaryKeyMixin):
    """Persisted record of an individual AI vulnerability prediction."""

    __tablename__ = "ai_predictions"

    scan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_snapshots.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_file_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_files.id", ondelete="SET NULL"), nullable=True, index=True
    )
    function_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("functions.id", ondelete="SET NULL"), nullable=True, index=True
    )

    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    function_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    line_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_line: Mapped[int | None] = mapped_column(Integer, nullable=True)

    prediction: Mapped[str] = mapped_column(String(50), nullable=False, default="VULNERABLE")
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    cwe_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)  # critical, high, medium, low
    cvss_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    evidence_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    provider: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    input_schema_version: Mapped[str] = mapped_column(String(50), nullable=False, default="v1.0.0")
    output_schema_version: Mapped[str] = mapped_column(String(50), nullable=False, default="v1.0.0")
    generated_by_ai: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    scan: Mapped["Scan"] = relationship("Scan")
    snapshot: Mapped["SourceSnapshot"] = relationship("SourceSnapshot")
    source_file: Mapped["SourceFile | None"] = relationship("SourceFile")
    function: Mapped["Function | None"] = relationship("Function")
    occurrences: Mapped[list["FindingOccurrence"]] = relationship("FindingOccurrence", back_populates="ai_prediction")
