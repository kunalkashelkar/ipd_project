# ============================================================
# XAI Explanation Schemas (Phase 6)
# ============================================================

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class GenerateExplanationRequest(BaseModel):
    """Payload to trigger an evidence-aware explanation or specific XAI method."""

    method: str = Field(
        default="evidence_synthesizer",
        description="Explanation method: evidence_synthesizer, integrated_gradients, shap, gnn_explainer, attention",
    )


class XAIExplanationResponse(BaseModel):
    """Normalized explanation schema presented to API consumers."""

    id: uuid.UUID
    finding_id: uuid.UUID
    prediction_id: uuid.UUID | None = None
    source_snapshot_id: uuid.UUID
    organization_id: uuid.UUID
    project_id: uuid.UUID

    provider: str
    model_name: str
    model_version: str
    explanation_method: str
    schema_version: str

    summary: str
    root_cause: str
    why_vulnerable: str
    impact: str
    evidence_explanation: str
    warnings: list[str] = Field(default_factory=list)
    confidence: float | None = None
    generated_by_ai: bool = True

    artifact_uri: str | None = None
    checksum: str | None = None

    important_locations: list[dict[str, Any]] = Field(default_factory=list)
    important_tokens: list[dict[str, Any]] = Field(default_factory=list)
    important_functions: list[dict[str, Any]] = Field(default_factory=list)
    important_nodes: list[dict[str, Any]] = Field(default_factory=list)
    important_edges: list[dict[str, Any]] = Field(default_factory=list)

    method_status: str
    status_reason: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
