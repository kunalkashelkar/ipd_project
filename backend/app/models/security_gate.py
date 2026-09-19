# ============================================================
# Security Gate, PR Security Result & Webhook Delivery Models (Phase 7)
# ============================================================

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.identifiers import PREFIX_PR_RESULT, generate_public_id
from backend.app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.organization import Organization
    from backend.app.models.project import Project
    from backend.app.models.repository import Repository
    from backend.app.models.scan import Scan


class SecurityGatePolicy(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Project-level Security Gate policy definition for PR/CI blocking."""

    __tablename__ = "security_gate_policies"
    __table_args__ = (
        UniqueConstraint("project_id", name="uq_project_security_gate_policy"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, default="Default Security Gate")
    version: Mapped[str] = mapped_column(String(20), nullable=False, default="v1.0.0")

    # Gate criteria
    block_new_critical: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    block_new_high: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    block_secrets: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    cvss_threshold: Mapped[float | None] = mapped_column(Float, nullable=True)  # e.g. 8.5+ fails

    # Relationships
    project: Mapped["Project"] = relationship("Project")
    organization: Mapped["Organization"] = relationship("Organization")


class PRSecurityResult(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Authoritative result of a Pull Request security scan and gate evaluation."""

    __tablename__ = "pr_security_results"

    public_id: Mapped[str] = mapped_column(
        String(32),
        unique=True,
        index=True,
        nullable=False,
        default=lambda: generate_public_id(PREFIX_PR_RESULT),
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    pull_request_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    pr_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    pr_head_sha: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    pr_base_sha: Mapped[str | None] = mapped_column(String(64), nullable=True)
    pr_branch: Mapped[str | None] = mapped_column(String(100), nullable=True)

    baseline_scan_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scans.id", ondelete="SET NULL"), nullable=True
    )
    pr_scan_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scans.id", ondelete="SET NULL"), nullable=True
    )

    # Finding comparison counts
    existing_findings_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    new_findings_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fixed_findings_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Gate decision
    gate_result: Mapped[str] = mapped_column(
        String(30), nullable=False, default="QUEUED"
    )  # PASSED, FAILED, SCAN_FAILED, ERROR, QUEUED
    gate_policy_version: Mapped[str] = mapped_column(String(20), nullable=False, default="v1.0.0")
    gate_details: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # GitHub integration reference
    github_check_run_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Workflow status
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="QUEUED"
    )  # QUEUED, SCANNING, COMPARING, GATE_EVALUATING, COMPLETED, FAILED
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    project: Mapped["Project"] = relationship("Project")
    repository: Mapped["Repository"] = relationship("Repository")
    baseline_scan: Mapped["Scan | None"] = relationship("Scan", foreign_keys=[baseline_scan_id])
    pr_scan: Mapped["Scan | None"] = relationship("Scan", foreign_keys=[pr_scan_id])


class WebhookDelivery(Base, UUIDPrimaryKeyMixin):
    """Replay protection and audit trail for external VCS webhook deliveries."""

    __tablename__ = "webhook_deliveries"

    delivery_id: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    repository_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("repositories.id", ondelete="SET NULL"), nullable=True, index=True
    )
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="processed")
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
