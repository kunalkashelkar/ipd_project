# ============================================================
# Source Snapshot, Source File, and Function Models (Phase 3)
# ============================================================

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
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

from backend.app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.git_meta import RepositoryCommit
    from backend.app.models.project import Project
    from backend.app.models.repository import Repository
    from backend.app.models.scan import Scan
    from backend.app.models.user import User


class SourceSnapshot(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """An immutable, canonical snapshot of source code for a project.

    Every vulnerability scan references a specific immutable source snapshot
    to ensure 100% reproducibility and strict provenance.
    """

    __tablename__ = "source_snapshots"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    repository_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("repositories.id", ondelete="SET NULL"), nullable=True, index=True
    )
    repository_commit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("repository_commits.id", ondelete="SET NULL"), nullable=True, index=True
    )
    source_type: Mapped[str] = mapped_column(
        String(30), nullable=False, index=True
    )  # upload_zip, upload_files, git, github
    source_version: Mapped[str | None] = mapped_column(String(100), nullable=True)  # commit SHA or upload version
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # SHA-256
    artifact_uri: Mapped[str] = mapped_column(String(1024), nullable=False)  # S3/MinIO original archive/tar key
    manifest_uri: Mapped[str | None] = mapped_column(String(1024), nullable=True)  # S3/MinIO manifest JSON key

    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="pending", index=True
    )  # pending, processing, ready, failed
    file_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    detected_languages: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    preprocessing_version: Mapped[str] = mapped_column(String(50), nullable=False, default="v1.0.0")

    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="snapshots")
    repository: Mapped["Repository | None"] = relationship("Repository", foreign_keys=[repository_id])
    commit: Mapped["RepositoryCommit | None"] = relationship("RepositoryCommit", foreign_keys=[repository_commit_id])
    creator: Mapped["User | None"] = relationship("User", foreign_keys=[created_by])
    source_files: Mapped[list["SourceFile"]] = relationship(
        "SourceFile", back_populates="snapshot", cascade="all, delete-orphan"
    )
    scans: Mapped[list["Scan"]] = relationship("Scan", back_populates="source_snapshot")


class SourceFile(Base, UUIDPrimaryKeyMixin):
    """A single source code file belonging to an immutable snapshot."""

    __tablename__ = "source_files"
    __table_args__ = (
        UniqueConstraint("source_snapshot_id", "relative_path", name="uq_snapshot_file_relpath"),
    )

    source_snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_snapshots.id", ondelete="CASCADE"), nullable=False, index=True
    )
    relative_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    path_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    language: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    original_artifact_uri: Mapped[str] = mapped_column(String(1024), nullable=False)
    normalized_artifact_uri: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    token_artifact_uri: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    line_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    encoding: Mapped[str] = mapped_column(String(30), nullable=False, default="utf-8")
    is_binary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_generated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    validation_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="valid"
    )  # valid, excluded, corrupt, unsupported
    preprocessing_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="pending"
    )  # pending, processed, failed

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    snapshot: Mapped["SourceSnapshot"] = relationship("SourceSnapshot", back_populates="source_files")
    functions: Mapped[list["Function"]] = relationship(
        "Function", back_populates="source_file", cascade="all, delete-orphan"
    )


class Function(Base, UUIDPrimaryKeyMixin):
    """An extracted function or method belonging to a source file."""

    __tablename__ = "functions"

    source_file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_files.id", ondelete="CASCADE"), nullable=False, index=True
    )
    function_id: Mapped[str] = mapped_column(
        String(128), nullable=False, index=True
    )  # deterministic provenance identity
    qualified_name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    language: Mapped[str | None] = mapped_column(String(50), nullable=True)
    start_line: Mapped[int] = mapped_column(Integer, nullable=False)
    end_line: Mapped[int] = mapped_column(Integer, nullable=False)
    start_byte: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_byte: Mapped[int | None] = mapped_column(Integer, nullable=True)
    signature: Mapped[str | None] = mapped_column(Text, nullable=True)

    original_content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    normalized_content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duplicate_group_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    extraction_status: Mapped[str] = mapped_column(String(30), nullable=False, default="extracted")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    source_file: Mapped["SourceFile"] = relationship("SourceFile", back_populates="functions")
