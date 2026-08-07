# ============================================================
# Scan Result Model
# ============================================================

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database.base import Base, UUIDPrimaryKeyMixin


class ScanResult(Base, UUIDPrimaryKeyMixin):
    """A single vulnerability prediction result from AI."""

    __tablename__ = "scan_results"

    scan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    function_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    line_number: Mapped[int | None] = mapped_column(Integer, nullable=True)

    severity: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # critical, high, medium, low, info
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    cvss_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    cwe_id: Mapped[str | None] = mapped_column(String(20), nullable=True)

    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommended_patch: Mapped[str | None] = mapped_column(Text, nullable=True)

    raw_prediction_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(50), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    scan: Mapped["Scan"] = relationship("Scan", back_populates="scan_results")  # noqa: F821
    feedback: Mapped[list["Feedback"]] = relationship(  # noqa: F821
        "Feedback", back_populates="scan_result", cascade="all, delete-orphan"
    )
