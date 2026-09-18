# ============================================================
# Remediation & Validation Schemas (Phase 6)
# ============================================================

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class GenerateRemediationRequest(BaseModel):
    """Payload to trigger remediation generation for a finding."""

    prompt_version: str = Field(default="v1.0.0", description="Prompt template version to use")


class RemediationReviewRequest(BaseModel):
    """Payload to approve or reject a proposed remediation."""

    decision: str = Field(..., description="'APPROVE' or 'REJECT'")
    comment: str | None = Field(default=None, description="Optional review comment or justification")


class ValidateRemediationRequest(BaseModel):
    """Payload to launch isolated multi-stage validation of a remediation."""

    run_tests: bool = Field(default=True, description="Whether to execute allowlisted tests in sandbox")
    validation_policy: str = Field(default="v1.0.0", description="Validation policy version")


class RemediationValidationResponse(BaseModel):
    """Structured result of an isolated validation attempt."""

    id: uuid.UUID
    remediation_id: uuid.UUID
    finding_id: uuid.UUID
    source_snapshot_id: uuid.UUID
    organization_id: uuid.UUID
    project_id: uuid.UUID

    attempt_number: int
    workspace_identifier: str
    validation_policy_version: str
    status: str
    started_at: datetime
    completed_at: datetime | None = None
    timeout_seconds: int

    patch_apply_result: dict[str, Any] = Field(default_factory=dict)
    syntax_result: dict[str, Any] = Field(default_factory=dict)
    build_result: dict[str, Any] = Field(default_factory=dict)
    test_result: dict[str, Any] = Field(default_factory=dict)
    static_analysis_result: dict[str, Any] = Field(default_factory=dict)
    taint_result: dict[str, Any] = Field(default_factory=dict)
    graph_result: dict[str, Any] = Field(default_factory=dict)
    regression_result: dict[str, Any] = Field(default_factory=dict)

    verification_scan_id: uuid.UUID | None = None
    final_verification_result: str
    failure_reason: str | None = None

    logs_artifact_uri: str | None = None
    artifact_checksum: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RemediationResponse(BaseModel):
    """Detailed remediation object."""

    id: uuid.UUID
    finding_id: uuid.UUID
    organization_id: uuid.UUID
    project_id: uuid.UUID
    source_snapshot_id: uuid.UUID

    remediation_number: int
    provider: str
    model_name: str
    model_version: str
    prompt_version: str
    status: str

    summary: str
    explanation: str
    diff_content: str
    patch_artifact_uri: str | None = None
    patch_checksum: str
    changed_files: list[str] = Field(default_factory=list)

    confidence: float | None = None
    warnings: list[str] = Field(default_factory=list)
    generated_by_ai: bool = True
    is_active_candidate: bool = True

    created_by_user_id: uuid.UUID | None = None
    reviewed_by_user_id: uuid.UUID | None = None
    reviewed_at: datetime | None = None
    review_comment: str | None = None
    superseded_by_id: uuid.UUID | None = None

    created_at: datetime
    updated_at: datetime

    validations: list[RemediationValidationResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class VerificationStatusResponse(BaseModel):
    """Authoritative finding verification status summary."""

    finding_id: uuid.UUID
    finding_status: str
    is_verified: bool
    active_remediation_id: uuid.UUID | None = None
    active_remediation_status: str | None = None
    latest_validation_id: uuid.UUID | None = None
    latest_validation_status: str | None = None
    verification_scan_id: uuid.UUID | None = None
    final_verification_result: str | None = None
    verified_at: datetime | None = None
    verification_details: dict[str, Any] = Field(default_factory=dict)


class RegisterModelVersionRequest(BaseModel):
    """Payload to register a new model version in the registry."""

    model_name: str
    version: str
    provider: str
    artifact_uri: str | None = None
    checksum: str | None = None
    runtime: str = "mock"
    input_schema_version: str = "v1.0.0"
    output_schema_version: str = "v1.0.0"
    status: str = "inactive"
    metadata_json: dict[str, Any] | None = None


class ModelVersionResponse(BaseModel):
    """Model version representation."""

    id: uuid.UUID
    model_name: str
    version: str
    provider: str
    artifact_uri: str | None = None
    checksum: str | None = None
    runtime: str
    input_schema_version: str
    output_schema_version: str
    status: str
    metadata_json: dict[str, Any] | None = None
    activated_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
