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


class ScanResponse(BaseModel):
    """Scan record response."""

    id: uuid.UUID
    project_id: uuid.UUID
    source_snapshot_id: uuid.UUID | None = None
    upload_id: uuid.UUID | None = None
    repository_id: uuid.UUID | None = None
    created_by: uuid.UUID | None = None
    status: str
    progress: float = 0.0
    current_stage: str | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    ai_model_version: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ScanStatusResponse(BaseModel):
    """Lightweight scan status for polling."""

    id: uuid.UUID
    status: str
    progress: float
    current_stage: str | None = None
    error_message: str | None = None

    model_config = {"from_attributes": True}
