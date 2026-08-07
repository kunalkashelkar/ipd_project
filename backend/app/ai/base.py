# ============================================================
# Base AI Model
# ============================================================

from __future__ import annotations

import abc

from backend.app.ai.contracts import AIInferenceRequest, AIPrediction


class BaseAIModel(abc.ABC):
    """Abstract base class for all AI prediction engines (mock or real)."""

    @property
    @abc.abstractmethod
    def version(self) -> str:
        """Return the model version identifier."""
        pass

    @abc.abstractmethod
    def load(self) -> None:
        """Load model weights / resources into memory."""
        pass

    @abc.abstractmethod
    def predict(self, request: AIInferenceRequest) -> list[AIPrediction]:
        """Run inference on the preprocessed functions."""
        pass

    @abc.abstractmethod
    def unload(self) -> None:
        """Free resources."""
        pass
