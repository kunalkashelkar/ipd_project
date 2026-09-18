# ============================================================
# AI Explanation Domain Model (Phase 6)
# ============================================================
# Persisted evidence-aware vulnerability explanations and
# normalized XAI attributions (Integrated Gradients, SHAP,
# GNNExplainer, Attention).
# ============================================================

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.ai_prediction import AIPrediction
    from backend.app.models.finding import Finding
    from backend.app.models.organization import Organization
    from backend.app.models.project import Project
    from backend.app.models.source_snapshot import SourceSnapshot


class AIExplanation(Base, UUIDPrimaryKeyMixin):
    """Persisted explainability record with normalized attribution and evidence synthesis."""

    __tablename__ = "ai_explanations"

    finding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("findings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    prediction_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_predictions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    source_snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_snapshots.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )

    provider: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    explanation_method: Mapped[str] = mapped_column(
        String(50), nullable=False, default="evidence_synthesizer", index=True
    )  # integrated_gradients, shap, gnn_explainer, attention, evidence_synthesizer
    schema_version: Mapped[str] = mapped_column(String(50), nullable=False, default="v1.0.0")

    summary: Mapped[str] = mapped_column(Text, nullable=False)
    root_cause: Mapped[str] = mapped_column(Text, nullable=False)
    why_vulnerable: Mapped[str] = mapped_column(Text, nullable=False)
    impact: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_explanation: Mapped[str] = mapped_column(Text, nullable=False)
    warnings: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    generated_by_ai: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Object storage reference for large raw attribution matrices (Captum / SHAP tensors)
    artifact_uri: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Compact normalized attributions stored directly in PostgreSQL
    important_locations: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    important_tokens: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    important_functions: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    important_nodes: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    important_edges: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)

    method_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="COMPLETED", index=True
    )  # COMPLETED, PARTIAL, NOT_SUPPORTED, FAILED
    status_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    finding: Mapped["Finding"] = relationship("Finding")
    prediction: Mapped["AIPrediction | None"] = relationship("AIPrediction")
    snapshot: Mapped["SourceSnapshot"] = relationship("SourceSnapshot")
    organization: Mapped["Organization"] = relationship("Organization")
    project: Mapped["Project"] = relationship("Project")
