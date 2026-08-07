# ============================================================
# Report Schemas
# ============================================================

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ReportCreate(BaseModel):
    """Request report generation."""

    scan_id: uuid.UUID
    format: str = Field(default="json", pattern="^(json|csv|pdf)$")


class ReportResponse(BaseModel):
    """Report record response."""

    id: uuid.UUID
    scan_id: uuid.UUID
    format: str
    status: str
    file_path: str | None = None
    generated_at: datetime | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
