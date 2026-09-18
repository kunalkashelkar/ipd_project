# ============================================================
# Explainable AI (XAI) Contracts (Phase 6)
# ============================================================
# Canonical data structures for evidence-aware vulnerability
# explanations, attribution methods, and model provenance.
# ============================================================

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ImportantLocation:
    """Normalized source code region identified as significant by XAI."""

    file_path: str
    start_line: int
    end_line: int
    importance: float
    description: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "file": self.file_path,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "importance": round(self.importance, 4),
            "description": self.description,
        }


@dataclass(frozen=True)
class ImportantToken:
    """Significant code token with attribution score."""

    token: str
    score: float
    file_path: str
    line_number: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "token": self.token,
            "score": round(self.score, 4),
            "file": self.file_path,
            "line": self.line_number,
        }


@dataclass(frozen=True)
class ImportantGraphNode:
    """Graph node highlighted by GNNExplainer."""

    node_id: str | int
    label: str
    importance: float
    node_type: str | None = None
    file_path: str | None = None
    line_number: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": str(self.node_id),
            "label": self.label,
            "importance": round(self.importance, 4),
            "node_type": self.node_type,
            "file": self.file_path,
            "line": self.line_number,
        }


@dataclass(frozen=True)
class ImportantGraphEdge:
    """Graph edge highlighted by GNNExplainer."""

    source: str | int
    target: str | int
    importance: float
    edge_type: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": str(self.source),
            "target": str(self.target),
            "importance": round(self.importance, 4),
            "edge_type": self.edge_type,
        }


@dataclass
class CanonicalXAIExplanation:
    """Canonical normalized explanation result from any XAI attribution provider."""

    provider: str
    model_name: str
    model_version: str
    explanation_method: str  # integrated_gradients, shap, gnn_explainer, attention, evidence_synthesizer
    summary: str
    root_cause: str
    why_vulnerable: str
    impact: str
    evidence_explanation: str
    important_locations: list[dict[str, Any]] = field(default_factory=list)
    important_tokens: list[dict[str, Any]] = field(default_factory=list)
    important_functions: list[dict[str, Any]] = field(default_factory=list)
    important_nodes: list[dict[str, Any]] = field(default_factory=list)
    important_edges: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    confidence: float | None = None
    method_status: str = "COMPLETED"  # COMPLETED, PARTIAL, NOT_SUPPORTED, FAILED
    status_reason: str | None = None
    raw_artifact_bytes: bytes | None = None
