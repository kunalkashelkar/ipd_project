# ============================================================
# Repository Model (Phase 2 Git Hierarchy)
# ============================================================

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.git_meta import RepositoryBranch, RepositoryCommit
    from backend.app.models.project import Project


class Repository(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A source code repository linked to a project."""

    __tablename__ = "repositories"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # github, gitlab, bitbucket, zip, folder
    repository_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    branch: Mapped[str | None] = mapped_column(String(100), nullable=True, default="main")
    commit_sha: Mapped[str | None] = mapped_column(String(64), nullable=True)
    auth_method: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # token, ssh, none
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="connected"
    )  # connected, syncing, synced, failed, disconnected
    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    disconnected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="repositories")
    branches: Mapped[list["RepositoryBranch"]] = relationship(
        "RepositoryBranch", back_populates="repository", cascade="all, delete-orphan"
    )
    commits: Mapped[list["RepositoryCommit"]] = relationship(
        "RepositoryCommit", back_populates="repository", cascade="all, delete-orphan"
    )
