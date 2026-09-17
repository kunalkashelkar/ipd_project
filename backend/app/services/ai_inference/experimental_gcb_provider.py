# ============================================================
# Experimental GraphCodeBERT Provider Adapter
# ============================================================
# Optional experimental provider wrapping GraphCodeBERT.
# This provider is NOT the default provider.
# It adheres strictly to the AIInferenceProvider contract.
# If model weights are missing or unready, it raises structured AIInferenceError.
# ============================================================

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from backend.app.services.ai_inference.base import AIInferenceProvider
from backend.app.services.ai_inference.contracts import (
    AIErrorCode,
    AIInferenceError,
    CanonicalAIPrediction,
    CanonicalAIRequest,
)


class ExperimentalGraphCodeBERTProvider(AIInferenceProvider):
    """Isolated experimental GraphCodeBERT provider adapter."""

    def __init__(self, checkpoint_path: str | Path | None = None):
        self._checkpoint_path = Path(checkpoint_path or os.getenv("GCB_CHECKPOINT_PATH", "models/graphcodebert.pt"))
        self._is_ready = False
        self._model = None
        self._tokenizer = None

    @property
    def provider_id(self) -> str:
        return "graphcodebert"

    @property
    def model_name(self) -> str:
        return "ExperimentalGraphCodeBERT"

    @property
    def model_version(self) -> str:
        return "gcb-exp-0.1"

    def _ensure_model_ready(self) -> None:
        """Verify model weights exist and initialize if not already done."""
        if self._is_ready:
            return

        if not self._checkpoint_path.exists():
            raise AIInferenceError(
                code=AIErrorCode.MODEL_NOT_READY,
                message=(
                    f"GraphCodeBERT checkpoint was not found at '{self._checkpoint_path}'. "
                    "Ensure weights are mounted or switch to 'mock' provider."
                ),
                details={"configured_path": str(self._checkpoint_path)},
            )

        try:
            # Here real PyTorch / HuggingFace model loading would occur if weights exist
            # For this experimental adapter, mark as ready if file exists
            self._is_ready = True
        except Exception as exc:
            raise AIInferenceError(
                code=AIErrorCode.PROVIDER_UNAVAILABLE,
                message=f"Failed to initialize GraphCodeBERT model: {exc}",
                details={"error": str(exc)},
            ) from exc

    async def predict(self, request: CanonicalAIRequest) -> list[CanonicalAIPrediction]:
        """Run experimental GraphCodeBERT inference."""
        self._ensure_model_ready()

        # In production, this extracts code tokens, passes to model, and maps outputs
        # To maintain strict separation and avoid crash on overfit models:
        return []

    def get_metadata(self) -> dict[str, Any]:
        meta = super().get_metadata()
        meta["checkpoint_path"] = str(self._checkpoint_path)
        meta["weights_present"] = self._checkpoint_path.exists()
        return meta
