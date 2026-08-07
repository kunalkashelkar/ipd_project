# ============================================================
# Result Schemas
# ============================================================

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ScanResultResponse(BaseModel):
    """Single scan result / vulnerability finding."""

    id: uuid.UUID
    scan_id: uuid.UUID
    file_path: str
    function_name: str | None = None
    line_number: int | None = None
    severity: str
    confidence: float
    cvss_score: float | None = None
    cwe_id: str | None = None
    explanation: str | None = None
    recommended_patch: str | None = None
    model_name: str | None = None
    model_version: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ResultSummary(BaseModel):
    """Aggregated summary of scan results."""

    scan_id: uuid.UUID
    total_vulnerabilities: int = 0
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    info: int = 0
    average_confidence: float = 0.0
    top_cwe: list[dict[str, Any]] = []


class FeedbackCreate(BaseModel):
    """Submit feedback on a scan result."""

    is_correct: bool
    comment: str | None = None


class FeedbackResponse(BaseModel):
    """Feedback response."""

    id: uuid.UUID
    scan_result_id: uuid.UUID
    user_id: uuid.UUID | None = None
    is_correct: bool
    comment: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
