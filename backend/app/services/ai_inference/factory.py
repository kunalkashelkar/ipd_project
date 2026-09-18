# ============================================================
# AI Inference Provider Factory
# ============================================================
# Central provider registry and factory.
# Enforces configuration-driven selection without silent fallbacks.
# ============================================================

from __future__ import annotations

from backend.app.core.config import get_settings
from backend.app.services.ai_inference.base import AIInferenceProvider
from backend.app.services.ai_inference.contracts import AIErrorCode, AIInferenceError
from backend.app.services.ai_inference.experimental_gcb_provider import (
    ExperimentalGraphCodeBERTProvider,
)
from backend.app.services.ai_inference.local_torch_provider import (
    LocalTorchProvider,
)
from backend.app.services.ai_inference.mock_provider import MockAIProvider


def get_ai_provider(provider_type: str | None = None) -> AIInferenceProvider:
    """Resolve and return the configured AI inference provider.
    
    Args:
        provider_type: Optional explicit provider identifier.
                       If None, resolves from system settings (get_settings().ai_mode).
                       
    Returns:
        Instance of AIInferenceProvider.
        
    Raises:
        AIInferenceError: If an unknown or unconfigured provider type is requested.
                          Does NOT silently fall back to mock when an explicit
                          non-mock provider is specified.
    """
    settings = get_settings()
    # Prefer explicit provider_type; fallback to settings.ai_mode (default: "mock")
    target = (provider_type or getattr(settings, "ai_mode", "mock") or "mock").strip().lower()

    if target in ("mock", "test", "development"):
        return MockAIProvider()

    if target in ("local_torch", "pytorch", "torch"):
        return LocalTorchProvider()

    if target in ("graphcodebert", "gcb", "experimental"):
        return ExperimentalGraphCodeBERTProvider()

    raise AIInferenceError(
        code=AIErrorCode.PROVIDER_UNAVAILABLE,
        message=f"Configured AI provider '{target}' is not recognized or supported.",
        details={"available_providers": ["mock", "local_torch", "graphcodebert"]},
    )
