# ============================================================
# Git Metadata Models — Branches and Commits
# ============================================================

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.repository import Repository


class RepositoryBranch(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A Git branch associated with a Repository."""

    __tablename__ = "repository_branches"
    __table_args__ = (
        UniqueConstraint("repository_id", "name", name="uq_repo_branch_name"),
    )

    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    head_commit_sha: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Relationships
    repository: Mapped["Repository"] = relationship("Repository", back_populates="branches")


class RepositoryCommit(Base, UUIDPrimaryKeyMixin):
    """A Git commit record associated with a Repository."""

    __tablename__ = "repository_commits"
    __table_args__ = (
        UniqueConstraint("repository_id", "commit_sha", name="uq_repo_commit_sha"),
    )

    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    commit_sha: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    author_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    author_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    committed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    repository: Mapped["Repository"] = relationship("Repository", back_populates="commits")
