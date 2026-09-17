# ============================================================
# Permanent AI Inference Provider Boundary
# ============================================================
# Abstract base class defining the AI Inference Provider contract.
# All real, experimental, and mock providers implement this interface.
# ============================================================

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from backend.app.services.ai_inference.contracts import (
    CanonicalAIPrediction,
    CanonicalAIRequest,
)


class AIInferenceProvider(ABC):
    """Permanent interface for vulnerability detection AI inference."""

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Unique identifier of the provider (e.g. 'mock', 'graphcodebert', 'hybrid')."""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Name of the underlying model."""
        ...

    @property
    @abstractmethod
    def model_version(self) -> str:
        """Version string of the model or ruleset."""
        ...

    @abstractmethod
    async def predict(self, request: CanonicalAIRequest) -> list[CanonicalAIPrediction]:
        """Perform inference on the canonical request.
        
        Args:
            request: Standardized request containing snapshot files, functions,
                     and canonical graph/taint references.
                     
        Returns:
            List of canonical AI predictions.
            
        Raises:
            AIInferenceError: On structured, anticipated failures (not unhandled exceptions).
        """
        ...

    def get_metadata(self) -> dict[str, Any]:
        """Return provider provenance and operational metadata."""
        return {
            "provider_id": self.provider_id,
            "model_name": self.model_name,
            "model_version": self.model_version,
        }
