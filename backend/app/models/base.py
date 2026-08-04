# Database Models — Phase 1 + 2 + 3 + 4 + 5 Tables
# ============================================================
# Defines ORM models for Projects, Uploads, Graphs,
# Predictions, Reports, Experiments, ParserJobs, TaintJobs, DatasetJobs, and TrainingJobs.
# ============================================================

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base


# ── Enums ──────────────────────────────────────────────────


class ProjectStatus(str, enum.Enum):
    CREATED = "created"
    UPLOADING = "uploading"
    PARSING = "parsing"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"


class UploadStatus(str, enum.Enum):
    PENDING = "pending"
    VALIDATED = "validated"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# ── Projects ──────────────────────────────────────────────


class Project(Base):
    """A top-level analysis project containing uploaded source files."""

    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus), default=ProjectStatus.CREATED, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    uploads: Mapped[list["Upload"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    graphs: Mapped[list["Graph"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    predictions: Mapped[list["Prediction"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    reports: Mapped[list["Report"]] = relationship(back_populates="project", cascade="all, delete-orphan")


# ── Uploads ───────────────────────────────────────────────


class Upload(Base):
    """A single uploaded file associated with a project."""

    __tablename__ = "uploads"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    file_extension: Mapped[str] = mapped_column(String(10), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA-256
    status: Mapped[UploadStatus] = mapped_column(
        Enum(UploadStatus), default=UploadStatus.PENDING, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    project: Mapped["Project"] = relationship(back_populates="uploads")


# ── Graphs ────────────────────────────────────────────────


class Graph(Base):
    """Stores metadata about a generated Code Property Graph (CPG)."""

    __tablename__ = "graphs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    graph_type: Mapped[str] = mapped_column(String(50), nullable=False)  # cpg, ast, cfg, dfg
    node_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    edge_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    storage_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    project: Mapped["Project"] = relationship(back_populates="graphs")


# ── Predictions ───────────────────────────────────────────


class Prediction(Base):
    """Stores a vulnerability prediction result for a project."""

    __tablename__ = "predictions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    vulnerability_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_vulnerable: Mapped[bool | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    project: Mapped["Project"] = relationship(back_populates="predictions")


# ── Reports ───────────────────────────────────────────────


class Report(Base):
    """An analysis report generated for a project."""

    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    report_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    project: Mapped["Project"] = relationship(back_populates="reports")


# ── Experiments ───────────────────────────────────────────


class Experiment(Base):
    """Tracks an ML experiment run with hyperparameters and results."""

    __tablename__ = "experiments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hyperparameters: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string
    accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    precision: Mapped[float | None] = mapped_column(Float, nullable=True)
    recall: Mapped[float | None] = mapped_column(Float, nullable=True)
    f1_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


# ── Parser Jobs ───────────────────────────────────────────


class ParserJobStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ParserJob(Base):
    """Tracks an asynchronous Joern CPG generation job."""

    __tablename__ = "parser_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    upload_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("uploads.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[ParserJobStatus] = mapped_column(
        Enum(ParserJobStatus), default=ParserJobStatus.QUEUED, nullable=False
    )

    # ── Source file info ───────────────────────────────────
    source_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    file_count: Mapped[int] = mapped_column(Integer, default=0)

    # ── Graph statistics ───────────────────────────────────
    function_count: Mapped[int] = mapped_column(Integer, default=0)
    ast_node_count: Mapped[int] = mapped_column(Integer, default=0)
    cfg_node_count: Mapped[int] = mapped_column(Integer, default=0)
    dfg_node_count: Mapped[int] = mapped_column(Integer, default=0)
    total_node_count: Mapped[int] = mapped_column(Integer, default=0)
    total_edge_count: Mapped[int] = mapped_column(Integer, default=0)

    # ── Output paths ──────────────────────────────────────
    graph_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    metadata_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    # ── Error tracking ────────────────────────────────────
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


# ── Taint Jobs ────────────────────────────────────────────


class TaintJobStatus(str, enum.Enum):
    QUEUED    = "queued"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"


class TaintJob(Base):
    """Tracks an asynchronous taint analysis job (Phase 3)."""

    __tablename__ = "taint_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    cpg_job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("parser_jobs.id", ondelete="SET NULL"), nullable=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[TaintJobStatus] = mapped_column(
        Enum(TaintJobStatus), default=TaintJobStatus.QUEUED, nullable=False
    )

    # ── Detection counts ────────────────────────────────
    source_count:        Mapped[int] = mapped_column(Integer, default=0)
    sink_count:          Mapped[int] = mapped_column(Integer, default=0)
    sanitizer_count:     Mapped[int] = mapped_column(Integer, default=0)
    tainted_node_count:  Mapped[int] = mapped_column(Integer, default=0)

    # ── Path severity breakdown ─────────────────────────
    attack_path_count:   Mapped[int] = mapped_column(Integer, default=0)
    critical_path_count: Mapped[int] = mapped_column(Integer, default=0)
    high_path_count:     Mapped[int] = mapped_column(Integer, default=0)
    medium_path_count:   Mapped[int] = mapped_column(Integer, default=0)
    low_path_count:      Mapped[int] = mapped_column(Integer, default=0)

    # ── Output paths ──────────────────────────────────
    security_graph_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    taint_report_path:   Mapped[str | None] = mapped_column(String(1024), nullable=True)

    # ── Error tracking ─────────────────────────────────
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    started_at:   Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at:   Mapped[datetime]        = mapped_column(DateTime(timezone=True), server_default=func.now())


# ── Dataset Jobs (Phase 4) ────────────────────────────────

class DatasetJobStatus(str, enum.Enum):
    QUEUED    = "queued"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"


class DatasetJob(Base):
    """Tracks asynchronous PyTorch Geometric dataset generation (Phase 4)."""

    __tablename__ = "dataset_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[DatasetJobStatus] = mapped_column(
        Enum(DatasetJobStatus), default=DatasetJobStatus.QUEUED, nullable=False
    )

    processed_graphs: Mapped[int] = mapped_column(Integer, default=0)
    failed_graphs:    Mapped[int] = mapped_column(Integer, default=0)
    total_graphs:     Mapped[int] = mapped_column(Integer, default=0)

    dataset_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    started_at:   Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at:   Mapped[datetime]        = mapped_column(DateTime(timezone=True), server_default=func.now())


# ── Training Jobs (Phase 5) ────────────────────────────────

class TrainingJobStatus(str, enum.Enum):
    QUEUED    = "queued"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"


class TrainingJob(Base):
    """Tracks asynchronous PyTorch training runs (Phase 5)."""

    __tablename__ = "training_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    dataset_job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dataset_jobs.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[TrainingJobStatus] = mapped_column(
        Enum(TrainingJobStatus), default=TrainingJobStatus.QUEUED, nullable=False
    )
    
    experiment_name: Mapped[str] = mapped_column(String(255), default="baseline")

    # Metrics
    best_epoch:   Mapped[int] = mapped_column(Integer, default=0)
    best_val_f1:  Mapped[float] = mapped_column(Float, default=0.0)
    test_acc:     Mapped[float] = mapped_column(Float, default=0.0)
    test_f1:      Mapped[float] = mapped_column(Float, default=0.0)
    test_roc_auc: Mapped[float] = mapped_column(Float, default=0.0)

    # Output paths
    checkpoint_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    metrics_path:    Mapped[str | None] = mapped_column(String(1024), nullable=True)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    started_at:   Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at:   Mapped[datetime]        = mapped_column(DateTime(timezone=True), server_default=func.now())
