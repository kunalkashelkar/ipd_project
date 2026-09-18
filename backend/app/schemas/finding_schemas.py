# ============================================================
# Finding Domain Schemas (Phase 5)
# ============================================================

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AIPredictionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    scan_id: uuid.UUID
    source_snapshot_id: uuid.UUID
    file_path: str
    function_name: str | None = None
    line_number: int | None = None
    end_line: int | None = None
    prediction: str
    confidence: float
    cwe_id: str | None = None
    severity: str
    cvss_score: float | None = None
    evidence_json: dict[str, Any] | None = None
    provider: str
    model_name: str
    model_version: str
    generated_by_ai: bool
    created_at: datetime


class FindingOccurrenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    finding_id: uuid.UUID
    scan_id: uuid.UUID
    source_snapshot_id: uuid.UUID
    file_path: str
    function_name: str | None = None
    start_line: int | None = None
    end_line: int | None = None
    location: dict[str, Any] | None = None
    ai_prediction_id: uuid.UUID | None = None
    static_evidence_ref: dict[str, Any] | None = None
    taint_evidence_ref: dict[str, Any] | None = None
    graph_evidence_ref: dict[str, Any] | None = None
    confidence: float
    severity: str
    observed_at: datetime
    ai_prediction: AIPredictionResponse | None = None


class FindingStatusHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    finding_id: uuid.UUID
    previous_status: str | None = None
    new_status: str
    actor_id: uuid.UUID | None = None
    reason: str | None = None
    change_metadata: dict[str, Any] | None = None
    created_at: datetime


class FindingAssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    finding_id: uuid.UUID
    assigned_to_user_id: uuid.UUID
    assigned_by_user_id: uuid.UUID | None = None
    active: bool
    created_at: datetime


class FindingCommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    finding_id: uuid.UUID
    author_id: uuid.UUID
    content: str
    created_at: datetime
    updated_at: datetime | None = None


class FindingSuppressionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    finding_id: uuid.UUID
    actor_id: uuid.UUID
    suppression_type: str
    reason: str
    expires_at: datetime | None = None
    active: bool
    created_at: datetime


class FindingListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    public_id: str | None = None
    project_id: uuid.UUID
    project_name: str | None = None
    project_public_id: str | None = None
    organization_id: uuid.UUID
    title: str
    vulnerability_type: str
    cwe_id: str | None = None
    severity: str
    cvss_score: float | None = None
    confidence: float
    risk_score: float
    status: str
    fingerprint: str
    first_seen_at: datetime
    last_seen_at: datetime
    fixed_at: datetime | None = None
    latest_file_path: str | None = None
    latest_line_number: int | None = None
    latest_scan_id: uuid.UUID | None = None
    latest_scan_public_id: str | None = None
    occurrence_count: int = 1


class FindingDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    public_id: str | None = None
    project_id: uuid.UUID
    project_public_id: str | None = None
    project_name: str | None = None
    organization_id: uuid.UUID
    title: str
    vulnerability_type: str
    cwe_id: str | None = None
    severity: str
    cvss_score: float | None = None
    confidence: float
    risk_score: float
    risk_version: str
    status: str
    fingerprint: str
    fingerprint_version: str
    first_seen_at: datetime
    last_seen_at: datetime
    fixed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    latest_occurrence: FindingOccurrenceResponse | None = None
    occurrences: list[FindingOccurrenceResponse] = []
    status_history: list[FindingStatusHistoryResponse] = []
    assignments: list[FindingAssignmentResponse] = []
    comments: list[FindingCommentResponse] = []
    suppressions: list[FindingSuppressionResponse] = []


class ProjectFindingsSummary(BaseModel):
    total: int = 0
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    open: int = 0
    confirmed: int = 0
    in_progress: int = 0
    fixed: int = 0
    suppressed: int = 0
    false_positive: int = 0
    risk_accepted: int = 0


class GlobalFindingsSummary(BaseModel):
    total: int = 0
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    info: int = 0


class FindingStatusTransitionRequest(BaseModel):
    status: str = Field(..., description="Target lifecycle status")
    reason: str | None = Field(None, max_length=1000, description="Optional reason or audit justification")


class FindingAssignRequest(BaseModel):
    user_id: uuid.UUID = Field(..., description="Organization member user UUID to assign")


class FindingCommentCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000, description="Comment message content")


class FindingSuppressionRequest(BaseModel):
    suppression_type: str = Field(
        ..., pattern="^(FALSE_POSITIVE|RISK_ACCEPTED|SUPPRESSED)$", description="Type of suppression"
    )
    reason: str = Field(..., min_length=3, max_length=2000, description="Justification reason")
    expires_at: datetime | None = Field(None, description="Optional expiration date")


class FindingSourceContextResponse(BaseModel):
    file_path: str
    language: str | None
    line_number: int | None
    start_line: int
    end_line: int
    source_snippet: str
    snapshot_id: uuid.UUID
    is_snapshot_immutable: bool = True
