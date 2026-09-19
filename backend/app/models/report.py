# ============================================================
# Report & ReportFile Models (Phase 7)
# ============================================================

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.identifiers import PREFIX_REPORT, generate_public_id
from backend.app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.organization import Organization
    from backend.app.models.project import Project
    from backend.app.models.scan import Scan
    from backend.app.models.user import User


class Report(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A generated analysis report for a scan or project."""

    __tablename__ = "reports"

    public_id: Mapped[str] = mapped_column(
        String(32),
        unique=True,
        index=True,
        nullable=False,
        default=lambda: generate_public_id(PREFIX_REPORT),
    )
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    scan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("scans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    report_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="security"
    )  # developer, security, executive
    format: Mapped[str] = mapped_column(
        String(10), nullable=False, default="json"
    )  # pdf, html, json, csv
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # pending, queued, generating, completed, failed
    file_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    generated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    config: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Relationships
    scan: Mapped["Scan"] = relationship("Scan", back_populates="reports")
    project: Mapped["Project | None"] = relationship("Project")
    organization: Mapped["Organization | None"] = relationship("Organization")
    creator: Mapped["User | None"] = relationship("User")
    files: Mapped[list["ReportFile"]] = relationship(
        "ReportFile", back_populates="report", cascade="all, delete-orphan", lazy="selectin"
    )


class ReportFile(Base, UUIDPrimaryKeyMixin):
    """A durable generated report artifact stored in object storage."""

    __tablename__ = "report_files"

    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    format: Mapped[str] = mapped_column(
        String(10), nullable=False
    )  # pdf, html, json, csv
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    report: Mapped["Report"] = relationship("Report", back_populates="files")
