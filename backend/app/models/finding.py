# ============================================================
# Finding Domain Models (Phase 5)
# ============================================================
# Permanent domain representation of software vulnerabilities:
# - Finding: Persistent security issue across scans.
# - FindingOccurrence: Immutable observation in a specific scan/snapshot.
# - FindingStatusHistory: Audit trail of lifecycle state transitions.
# - FindingAssignment: Assignment to organization members.
# - FindingComment: Team collaboration notes.
# - FindingSuppression: False positive / risk acceptance / suppression.
# ============================================================

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
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

from backend.app.core.identifiers import PREFIX_FINDING, generate_public_id
from backend.app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.ai_prediction import AIPrediction
    from backend.app.models.organization import Organization
    from backend.app.models.project import Project
    from backend.app.models.scan import Scan
    from backend.app.models.source_snapshot import SourceSnapshot
    from backend.app.models.user import User


class Finding(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Persistent vulnerability finding across multiple scans within a project."""

    __tablename__ = "findings"
    __table_args__ = (
        UniqueConstraint("project_id", "fingerprint", name="uq_project_finding_fingerprint"),
    )

    public_id: Mapped[str] = mapped_column(
        String(32),
        unique=True,
        index=True,
        nullable=False,
        default=lambda: generate_public_id(PREFIX_FINDING),
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    vulnerability_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    cwe_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)

    severity: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # critical, high, medium, low
    cvss_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    risk_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, index=True)
    risk_version: Mapped[str] = mapped_column(String(20), nullable=False, default="v1.0")

    # Status: OPEN, CONFIRMED, IN_PROGRESS, FIX_PROPOSED, UNDER_REVIEW, FIXED, VERIFIED, FALSE_POSITIVE, RISK_ACCEPTED, SUPPRESSED, REOPENED
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="OPEN", index=True)

    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    fingerprint_version: Mapped[str] = mapped_column(String(20), nullable=False, default="v1.0")

    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fixed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    project: Mapped["Project"] = relationship("Project")
    organization: Mapped["Organization"] = relationship("Organization")
    occurrences: Mapped[list["FindingOccurrence"]] = relationship(
        "FindingOccurrence", back_populates="finding", cascade="all, delete-orphan"
    )
    status_history: Mapped[list["FindingStatusHistory"]] = relationship(
        "FindingStatusHistory", back_populates="finding", cascade="all, delete-orphan", order_by="FindingStatusHistory.created_at.desc()"
    )
    assignments: Mapped[list["FindingAssignment"]] = relationship(
        "FindingAssignment", back_populates="finding", cascade="all, delete-orphan"
    )
    comments: Mapped[list["FindingComment"]] = relationship(
        "FindingComment", back_populates="finding", cascade="all, delete-orphan", order_by="FindingComment.created_at.asc()"
    )
    suppressions: Mapped[list["FindingSuppression"]] = relationship(
        "FindingSuppression", back_populates="finding", cascade="all, delete-orphan"
    )


class FindingOccurrence(Base, UUIDPrimaryKeyMixin):
    """Immutable observation of a finding in a specific scan and source snapshot."""

    __tablename__ = "finding_occurrences"

    finding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("findings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    scan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_snapshots.id", ondelete="CASCADE"), nullable=False, index=True
    )

    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    function_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    start_line: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_line: Mapped[int | None] = mapped_column(Integer, nullable=True)
    location: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    ai_prediction_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_predictions.id", ondelete="SET NULL"), nullable=True, index=True
    )

    static_evidence_ref: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    taint_evidence_ref: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    graph_evidence_ref: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    finding: Mapped["Finding"] = relationship("Finding", back_populates="occurrences")
    scan: Mapped["Scan"] = relationship("Scan")
    snapshot: Mapped["SourceSnapshot"] = relationship("SourceSnapshot")
    ai_prediction: Mapped["AIPrediction | None"] = relationship("AIPrediction", back_populates="occurrences")


class FindingStatusHistory(Base, UUIDPrimaryKeyMixin):
    """Historical record of finding lifecycle status transitions."""

    __tablename__ = "finding_status_history"

    finding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("findings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    previous_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    new_status: Mapped[str] = mapped_column(String(50), nullable=False)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    change_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    finding: Mapped["Finding"] = relationship("Finding", back_populates="status_history")
    actor: Mapped["User | None"] = relationship("User")


class FindingAssignment(Base, UUIDPrimaryKeyMixin):
    """Assignment of a finding to an organization member."""

    __tablename__ = "finding_assignments"

    finding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("findings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    assigned_to_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    assigned_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    finding: Mapped["Finding"] = relationship("Finding", back_populates="assignments")
    assigned_to: Mapped["User"] = relationship("User", foreign_keys=[assigned_to_user_id])
    assigned_by: Mapped["User | None"] = relationship("User", foreign_keys=[assigned_by_user_id])


class FindingComment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Team collaboration comment on a finding."""

    __tablename__ = "finding_comments"

    finding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("findings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Relationships
    finding: Mapped["Finding"] = relationship("Finding", back_populates="comments")
    author: Mapped["User"] = relationship("User")


class FindingSuppression(Base, UUIDPrimaryKeyMixin):
    """Record of finding suppression, false positive marking, or risk acceptance."""

    __tablename__ = "finding_suppressions"

    finding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("findings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    actor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    suppression_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # FALSE_POSITIVE, RISK_ACCEPTED, SUPPRESSED
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    finding: Mapped["Finding"] = relationship("Finding", back_populates="suppressions")
    actor: Mapped["User"] = relationship("User")
