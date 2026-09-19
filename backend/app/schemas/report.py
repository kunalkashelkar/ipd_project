# ============================================================
# Report Schemas (Phase 7)
# ============================================================

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ReportCreate(BaseModel):
    """Request asynchronous report generation."""

    scan_id: str
    format: str = Field(default="json", pattern="^(json|csv|pdf|html)$")
    report_type: str = Field(default="security", pattern="^(developer|security|executive)$")
    config: dict[str, Any] | None = None


class ReportFileResponse(BaseModel):
    """Report artifact file metadata."""

    id: uuid.UUID
    format: str
    storage_key: str
    content_type: str
    size_bytes: int
    checksum_sha256: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ReportResponse(BaseModel):
    """Authoritative report record response."""

    id: uuid.UUID
    public_id: str
    organization_id: uuid.UUID | None = None
    project_id: uuid.UUID | None = None
    scan_id: uuid.UUID
    report_type: str = "security"
    format: str
    status: str
    file_path: str | None = None
    generated_at: datetime | None = None
    error_message: str | None = None
    files: list[ReportFileResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
