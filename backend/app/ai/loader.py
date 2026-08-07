# ============================================================
# AI Model Loader
# ============================================================

from __future__ import annotations

import threading

from backend.app.ai.base import BaseAIModel
from backend.app.ai.mock import MockAIModel
from backend.app.core.config import get_settings


class AILoader:
    """Singleton registry that holds the loaded AI model in memory."""

    _instance: BaseAIModel | None = None
    _lock = threading.Lock()

    @classmethod
    def get_model(cls) -> BaseAIModel:
        """Get the loaded AI model, instantiating it if necessary."""
        if cls._instance is None:
            with cls._lock:
                # Double-checked locking
                if cls._instance is None:
                    settings = get_settings()

                    if settings.ai_mode == "mock":
                        cls._instance = MockAIModel()
                    elif settings.ai_mode == "production":
                        # Future ML integration goes here
                        raise NotImplementedError("Production AI model not yet implemented")
                    else:
                        raise ValueError(f"Unknown AI mode: {settings.ai_mode}")

                    # Load weights into memory
                    cls._instance.load()

        return cls._instance
