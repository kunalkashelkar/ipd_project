# ============================================================
# Project Model (Phase 2 Multi-Tenant)
# ============================================================

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.organization import Organization
    from backend.app.models.repository import Repository
    from backend.app.models.scan import Scan
    from backend.app.models.source_snapshot import SourceSnapshot
    from backend.app.models.upload import Upload
    from backend.app.models.user import User


class Project(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A project containing code repositories and scans, strictly scoped to an Organization."""

    __tablename__ = "projects"
    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_project_org_name"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str | None] = mapped_column(String(50), nullable=True)
    default_branch: Mapped[str | None] = mapped_column(String(100), nullable=True, default="main")

    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization", back_populates="projects")
    owner: Mapped["User"] = relationship(
        "User", back_populates="projects", foreign_keys=[owner_id]
    )
    repositories: Mapped[list["Repository"]] = relationship(
        "Repository", back_populates="project", cascade="all, delete-orphan"
    )
    uploads: Mapped[list["Upload"]] = relationship(
        "Upload", back_populates="project", cascade="all, delete-orphan"
    )
    snapshots: Mapped[list["SourceSnapshot"]] = relationship(
        "SourceSnapshot", back_populates="project", cascade="all, delete-orphan"
    )
    scans: Mapped[list["Scan"]] = relationship(
        "Scan", back_populates="project", cascade="all, delete-orphan"
    )
