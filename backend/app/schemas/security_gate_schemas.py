# ============================================================
# Security Gate & PR Result Schemas (Phase 7)
# ============================================================

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SecurityGatePolicyUpdate(BaseModel):
    """Update project security gate policy."""

    name: str | None = None
    block_new_critical: bool | None = None
    block_new_high: bool | None = None
    block_secrets: bool | None = None
    cvss_threshold: float | None = Field(default=None, ge=0.0, le=10.0)


class SecurityGatePolicyResponse(BaseModel):
    """Security gate policy response."""

    id: uuid.UUID
    project_id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    version: str
    block_new_critical: bool
    block_new_high: bool
    block_secrets: bool
    cvss_threshold: float | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PRSecurityResultResponse(BaseModel):
    """PR security evaluation result response."""

    id: uuid.UUID
    public_id: str
    organization_id: uuid.UUID
    project_id: uuid.UUID
    repository_id: uuid.UUID
    pull_request_number: int
    pr_title: str | None = None
    pr_head_sha: str
    pr_base_sha: str | None = None
    pr_branch: str | None = None
    baseline_scan_id: uuid.UUID | None = None
    pr_scan_id: uuid.UUID | None = None
    existing_findings_count: int
    new_findings_count: int
    fixed_findings_count: int
    gate_result: str
    gate_policy_version: str
    gate_details: dict[str, Any] | None = None
    status: str
    failure_reason: str | None = None
    completed_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
