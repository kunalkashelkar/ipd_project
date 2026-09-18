# ============================================================
# Remediation & Validation Domain Models (Phase 6)
# ============================================================
# Manages LLM-assisted vulnerability remediations, unified diff
# patches, human review state, and isolated multi-stage validation.
# ============================================================

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.finding import Finding
    from backend.app.models.organization import Organization
    from backend.app.models.project import Project
    from backend.app.models.scan import Scan
    from backend.app.models.source_snapshot import SourceSnapshot
    from backend.app.models.user import User


class Remediation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Proposed code remediation for a security finding."""

    __tablename__ = "remediations"

    finding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("findings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_snapshots.id", ondelete="CASCADE"), nullable=False, index=True
    )

    remediation_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    provider: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=False, default="v1.0.0")

    # Status: PROPOSED, GENERATED, APPLIED, VALIDATING, VALIDATED, FAILED_VALIDATION, REJECTED, APPROVED, SUPERSEDED
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="GENERATED", index=True)

    summary: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    diff_content: Mapped[str] = mapped_column(Text, nullable=False)
    patch_artifact_uri: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    patch_checksum: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA-256
    changed_files: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)

    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    warnings: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    generated_by_ai: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_active_candidate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)

    # Human review & lifecycle attribution
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    superseded_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("remediations.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    finding: Mapped["Finding"] = relationship("Finding")
    snapshot: Mapped["SourceSnapshot"] = relationship("SourceSnapshot")
    organization: Mapped["Organization"] = relationship("Organization")
    project: Mapped["Project"] = relationship("Project")
    created_by: Mapped["User | None"] = relationship("User", foreign_keys=[created_by_user_id])
    reviewed_by: Mapped["User | None"] = relationship("User", foreign_keys=[reviewed_by_user_id])
    validations: Mapped[list["RemediationValidation"]] = relationship(
        "RemediationValidation", back_populates="remediation", cascade="all, delete-orphan", order_by="RemediationValidation.attempt_number.desc()"
    )


class RemediationValidation(Base, UUIDPrimaryKeyMixin):
    """Isolated multi-stage validation attempt for a proposed remediation."""

    __tablename__ = "remediation_validations"

    remediation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("remediations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    finding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("findings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_snapshots.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )

    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    workspace_identifier: Mapped[str] = mapped_column(String(255), nullable=False)
    validation_policy_version: Mapped[str] = mapped_column(String(50), nullable=False, default="v1.0.0")

    # Status: PREPARING, RUNNING, PASSED, FAILED, TIMED_OUT
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="PREPARING", index=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=300)

    # Structured multi-stage results
    patch_apply_result: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    syntax_result: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    build_result: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    test_result: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    static_analysis_result: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    taint_result: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    graph_result: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    regression_result: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    verification_scan_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scans.id", ondelete="SET NULL"), nullable=True, index=True
    )
    final_verification_result: Mapped[str] = mapped_column(
        String(50), nullable=False, default="PENDING", index=True
    )  # VERIFIED, NOT_VERIFIED, FAILED, PENDING
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    logs_artifact_uri: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    artifact_checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    remediation: Mapped["Remediation"] = relationship("Remediation", back_populates="validations")
    finding: Mapped["Finding"] = relationship("Finding")
    snapshot: Mapped["SourceSnapshot"] = relationship("SourceSnapshot")
    verification_scan: Mapped["Scan | None"] = relationship("Scan")
