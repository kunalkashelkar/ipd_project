# ============================================================
# Analysis Artifact Model (Phase 4 Canonical Artifact Contract)
# ============================================================

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.scan import Scan
    from backend.app.models.source_snapshot import SourceSnapshot


class AnalysisArtifact(Base, UUIDPrimaryKeyMixin):
    """Canonical analysis artifact generated during static analysis.

    Stores metadata for AST, CFG, PDG, CPG, CALL_GRAPH, TAINT, etc.
    The actual graph content resides in object storage (MinIO/S3)
    referenced by artifact_uri, with strict SHA-256 cryptographic verification.
    """

    __tablename__ = "analysis_artifacts"
    __table_args__ = (
        UniqueConstraint("scan_id", "artifact_type", name="uq_scan_artifact_type"),
    )

    scan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_snapshots.id", ondelete="CASCADE"), nullable=False, index=True
    )
    artifact_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # AST, CFG, PDG, CPG, CALL_GRAPH, DATA_FLOW, POINTER_ANALYSIS, TAINT, COMPLEXITY, API_USAGE
    schema_version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0.0")
    artifact_uri: Mapped[str] = mapped_column(String(1024), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="ready", index=True
    )  # ready, failed, unsupported
    tool_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tool_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    config_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    node_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    edge_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    artifact_metadata: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    scan: Mapped["Scan"] = relationship("Scan", back_populates="artifacts")
    source_snapshot: Mapped["SourceSnapshot"] = relationship("SourceSnapshot")
