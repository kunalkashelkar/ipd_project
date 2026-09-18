# ============================================================
# Scan Model
# ============================================================

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.identifiers import PREFIX_SCAN, generate_public_id
from backend.app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Scan(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A vulnerability analysis scan execution."""

    __tablename__ = "scans"

    public_id: Mapped[str] = mapped_column(
        String(32),
        unique=True,
        index=True,
        nullable=False,
        default=lambda: generate_public_id(PREFIX_SCAN),
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True
    )
    upload_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("uploads.id", ondelete="SET NULL"), nullable=True
    )
    repository_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("repositories.id", ondelete="SET NULL"), nullable=True
    )
    source_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_snapshots.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="pending", index=True
    )  # pending, queued, preparing, checkout, preprocessing, static_analysis, graph_processing, ai_analysis, post_processing, completed, failed, cancelled, timed_out, retrying
    progress: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)  # 0 to 100
    current_stage: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    stage_attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    worker_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=1800)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ai_model_version: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="scans")  # noqa: F821
    upload: Mapped["Upload | None"] = relationship("Upload", back_populates="scans")  # noqa: F821
    source_snapshot: Mapped["SourceSnapshot | None"] = relationship(  # noqa: F821
        "SourceSnapshot", back_populates="scans"
    )
    scan_logs: Mapped[list["ScanLog"]] = relationship(  # noqa: F821
        "ScanLog", back_populates="scan", cascade="all, delete-orphan"
    )
    scan_results: Mapped[list["ScanResult"]] = relationship(  # noqa: F821
        "ScanResult", back_populates="scan", cascade="all, delete-orphan"
    )
    reports: Mapped[list["Report"]] = relationship(  # noqa: F821
        "Report", back_populates="scan", cascade="all, delete-orphan"
    )
    stage_runs: Mapped[list["ScanStageRun"]] = relationship(
        "ScanStageRun", back_populates="scan", cascade="all, delete-orphan", order_by="ScanStageRun.created_at"
    )
    events: Mapped[list["ScanEvent"]] = relationship(
        "ScanEvent", back_populates="scan", cascade="all, delete-orphan", order_by="ScanEvent.created_at"
    )
    artifacts: Mapped[list["AnalysisArtifact"]] = relationship(  # noqa: F821
        "AnalysisArtifact", back_populates="scan", cascade="all, delete-orphan"
    )


class ScanStageRun(Base, UUIDPrimaryKeyMixin):
    """Execution history of a specific stage in a scan."""

    __tablename__ = "scan_stage_runs"
    __table_args__ = (
        UniqueConstraint("scan_id", "stage", "attempt", name="uq_scan_stage_attempt"),
    )

    scan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stage: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="pending"
    )  # pending, running, completed, failed, skipped, cancelled, timed_out
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    worker_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    stage_metadata: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    scan: Mapped["Scan"] = relationship("Scan", back_populates="stage_runs")


class ScanEvent(Base, UUIDPrimaryKeyMixin):
    """Audit and timeline event emitted during scan lifecycle."""

    __tablename__ = "scan_events"

    scan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    stage: Mapped[str | None] = mapped_column(String(50), nullable=True)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    scan: Mapped["Scan"] = relationship("Scan", back_populates="events")

