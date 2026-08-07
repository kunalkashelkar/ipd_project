# ============================================================
# AI Contracts — The Stable Interface
# ============================================================
# The rest of the backend only knows about these Pydantic models.
# It does NOT know about PyTorch, Transformers, or Mock logic.
# ============================================================

from __future__ import annotations

from pydantic import BaseModel


class AIPrediction(BaseModel):
    """A single vulnerability prediction from the AI model."""

    file_path: str
    function_name: str | None = None
    line_number: int | None = None
    severity: str  # critical, high, medium, low, info
    confidence: float  # 0.0 to 1.0
    cwe_id: str | None = None
    explanation: str
    recommended_patch: str | None = None
    model_version: str


class AIInferenceRequest(BaseModel):
    """Input payload to the AI predictor."""

    scan_id: str
    language: str
    functions: list[dict]  # Output from preprocessing
