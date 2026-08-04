# ============================================================
# API Schemas — Pydantic models for request / response bodies
# ============================================================

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


# ── Health ─────────────────────────────────────────────────


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "0.1.0"
    environment: str = "development"


# ── Status ─────────────────────────────────────────────────


class StatusResponse(BaseModel):
    status: str = "ok"
    database: str = "connected"
    uptime_seconds: float = 0.0


# ── Projects ──────────────────────────────────────────────


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None


class ProjectResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectListResponse(BaseModel):
    projects: list[ProjectResponse]
    total: int


# ── Uploads ───────────────────────────────────────────────


class UploadResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    filename: str
    original_filename: str
    file_size: int
    file_extension: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class UploadListResponse(BaseModel):
    uploads: list[UploadResponse]
    total: int


# ── Generic ───────────────────────────────────────────────


class MessageResponse(BaseModel):
    message: str
    detail: str | None = None


# ── Parser ─────────────────────────────────────────────────


class ParseRequest(BaseModel):
    """Request body for POST /parse."""
    upload_id: uuid.UUID
    project_id: uuid.UUID | None = None


class ParseJobResponse(BaseModel):
    """Immediate response when a parse job is queued."""
    job_id: uuid.UUID
    status: str = "queued"
    message: str = "Parse job queued. Poll GET /parse/{job_id} for status."


class ParseStatusResponse(BaseModel):
    """Full status of a parse job, returned by GET /parse/{job_id}."""
    job_id: uuid.UUID
    project_id: uuid.UUID
    status: str
    file_count: int = 0
    function_count: int = 0
    ast_nodes: int = 0
    cfg_nodes: int = 0
    dfg_nodes: int = 0
    total_nodes: int = 0
    total_edges: int = 0
    graph_path: str | None = None
    metadata_path: str | None = None
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


# ── Graph (for viewer) ────────────────────────────────────


class GraphNodeSchema(BaseModel):
    id: str
    label: str | None = None
    code: str | None = None
    line_number: int | None = None
    filename: str | None = None
    layers: list[str] = []


class GraphEdgeSchema(BaseModel):
    source: str
    target: str
    label: str | None = None
    layer: str | None = None
    variable: str | None = None


class GraphResponse(BaseModel):
    """Graph data returned by GET /parse/{job_id}/graph for the frontend viewer."""
    job_id: uuid.UUID
    nodes: list[GraphNodeSchema]
    edges: list[GraphEdgeSchema]
    statistics: dict = {}


# ── Taint Analysis ─────────────────────────────────────────


class TaintRequest(BaseModel):
    """Request body for POST /taint/analyze."""
    cpg_job_id: uuid.UUID
    project_id: uuid.UUID | None = None


class TaintJobResponse(BaseModel):
    """Immediate 202 response when a taint job is queued."""
    taint_job_id: uuid.UUID
    cpg_job_id: uuid.UUID
    status: str = "queued"
    message: str = "Taint analysis queued."


class TaintStatusResponse(BaseModel):
    """Status and summary statistics of a taint job."""
    taint_job_id: uuid.UUID
    cpg_job_id: uuid.UUID
    status: str
    source_count: int = 0
    sink_count: int = 0
    sanitizer_count: int = 0
    tainted_node_count: int = 0
    attack_path_count: int = 0
    critical_path_count: int = 0
    high_path_count: int = 0
    medium_path_count: int = 0
    low_path_count: int = 0
    security_graph_path: str | None = None
    taint_report_path: str | None = None
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


class AttackPathSchema(BaseModel):
    """A single source-to-sink taint flow."""
    path_id: str
    source_node_id: str
    sink_node_id: str
    nodes: list[str]
    length: int
    sanitized: bool
    severity: str
    risk_score: float
    sink_category: str = ""
    source_category: str = ""
    source_code: str = ""
    sink_code: str = ""
    source_line: int | None = None
    sink_line: int | None = None
    filename: str | None = None


class TaintReportResponse(BaseModel):
    """Full taint analysis report including all attack paths."""
    taint_job_id: uuid.UUID
    cpg_job_id: uuid.UUID
    summary: dict = {}
    attack_paths: list[AttackPathSchema] = []

# ── Dataset Processing ──────────────────────────────────────


class DatasetRequest(BaseModel):
    """Request body for POST /dataset/build."""
    project_id: uuid.UUID


class DatasetJobResponse(BaseModel):
    """Immediate 202 response when a dataset job is queued."""
    dataset_job_id: uuid.UUID
    project_id: uuid.UUID
    status: str = "queued"
    message: str = "Dataset processing queued."


class DatasetStatusResponse(BaseModel):
    """Status and summary statistics of a dataset job."""
    dataset_job_id: uuid.UUID
    project_id: uuid.UUID
    status: str
    processed_graphs: int = 0
    failed_graphs: int = 0
    total_graphs: int = 0
    dataset_path: str | None = None
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


# ── Model Training & Inference (Phase 5) ────────────────────


class TrainRequest(BaseModel):
    """Request body for POST /model/train."""
    dataset_job_id: uuid.UUID
    experiment_name: str = "baseline"
    hidden_dim: int = 256
    heads: int = 4
    learning_rate: float = 0.001
    epochs: int = 50


class TrainJobResponse(BaseModel):
    """Immediate 202 response when a training job is queued."""
    training_job_id: uuid.UUID
    dataset_job_id: uuid.UUID
    status: str = "queued"
    message: str = "Training job queued."


class TrainStatusResponse(BaseModel):
    """Status and metrics of a training job."""
    training_job_id: uuid.UUID
    dataset_job_id: uuid.UUID | None = None
    experiment_name: str
    status: str
    best_epoch: int = 0
    best_val_f1: float = 0.0
    test_acc: float = 0.0
    test_f1: float = 0.0
    test_roc_auc: float = 0.0
    checkpoint_path: str | None = None
    metrics_path: str | None = None
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


class PredictRequest(BaseModel):
    """Request body for POST /model/predict."""
    cpg_job_id: uuid.UUID
    checkpoint_path: str | None = None


# ── Semantic Integration (Phase 6) ────────────────────────
class EmbedRequest(BaseModel):
    """Request body for POST /semantic/embed."""
    code: list[str]

class EmbedResponse(BaseModel):
    """Response containing 768-D code embeddings."""
    embeddings: list[list[float]]
    dim: int = 768



