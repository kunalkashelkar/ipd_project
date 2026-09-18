# ============================================================
# Scan Schemas
# ============================================================

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ScanCreate(BaseModel):
    """Create a new scan."""

    project_id: uuid.UUID
    source_snapshot_id: uuid.UUID | None = None
    upload_id: uuid.UUID | None = None
    repository_id: uuid.UUID | None = None
    idempotency_key: str | None = None
    config: dict | None = None


class ScanResponse(BaseModel):
    """Scan record response."""

    id: uuid.UUID
    public_id: str | None = None
    project_id: uuid.UUID
    project_name: str | None = None
    project_public_id: str | None = None
    organization_id: uuid.UUID | None = None
    source_snapshot_id: uuid.UUID | None = None
    source_snapshot_version: str | None = None
    source_snapshot_public_id: str | None = None
    upload_id: uuid.UUID | None = None
    repository_id: uuid.UUID | None = None
    created_by: uuid.UUID | None = None
    status: str
    progress: float = 0.0
    current_stage: str | None = None
    stage_attempt: int = 1
    retry_count: int = 0
    timeout_seconds: int = 1800
    worker_id: str | None = None
    heartbeat_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    cancelled_at: datetime | None = None
    failure_code: str | None = None
    failure_reason: str | None = None
    error_message: str | None = None
    config: dict | None = None
    ai_model_version: str | None = None
    purpose: str | None = "GENERAL_SCAN"
    finding_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ScanStatusResponse(BaseModel):
    """Lightweight scan status for polling."""

    id: uuid.UUID
    status: str
    progress: float
    current_stage: str | None = None
    failure_code: str | None = None
    failure_reason: str | None = None
    cancelled_at: datetime | None = None
    error_message: str | None = None

    model_config = {"from_attributes": True}


class ScanStageRunResponse(BaseModel):
    """Execution history of a specific scan stage."""

    id: uuid.UUID
    scan_id: uuid.UUID
    stage: str
    attempt: int
    status: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_seconds: float | None = None
    error_code: str | None = None
    error_message: str | None = None
    metadata: dict | None = Field(default=None, alias="stage_metadata")
    created_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class AnalysisArtifactResponse(BaseModel):
    """Metadata for canonical analysis artifacts (AST, CFG, PDG, CPG, CALL_GRAPH, TAINT)."""

    id: uuid.UUID
    scan_id: uuid.UUID
    source_snapshot_id: uuid.UUID
    artifact_type: str
    schema_version: str = "1.0.0"
    artifact_uri: str
    content_hash: str
    size_bytes: int = 0
    status: str
    tool_name: str | None = None
    tool_version: str | None = None
    node_count: int = 0
    edge_count: int = 0
    metadata: dict | None = Field(default=None, alias="artifact_metadata")
    created_at: datetime
    completed_at: datetime | None = None
    error_message: str | None = None

    model_config = {"from_attributes": True, "populate_by_name": True}

