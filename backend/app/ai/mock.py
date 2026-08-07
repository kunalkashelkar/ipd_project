# ============================================================
# Mock AI Model
# ============================================================

from __future__ import annotations

import random
import time

from backend.app.ai.base import BaseAIModel
from backend.app.ai.contracts import AIInferenceRequest, AIPrediction
from backend.app.core.logging import logger


class MockAIModel(BaseAIModel):
    """A mock implementation for development without ML dependencies."""

    @property
    def version(self) -> str:
        return "mock-v1.0"

    def load(self) -> None:
        logger.info("Mock AI model 'loaded' into memory")
        time.sleep(1)  # Simulate load time

    def predict(self, request: AIInferenceRequest) -> list[AIPrediction]:
        """Simulate vulnerability detection by randomly flagging functions."""
        predictions = []

        logger.info(
            "Mock AI analyzing {count} functions for scan {scan_id}",
            count=len(request.functions),
            scan_id=request.scan_id,
        )

        for func in request.functions:
            # Simulate processing time per function
            time.sleep(0.1)

            # 10% chance to flag a function in mock mode
            if random.random() < 0.10:
                severity = random.choice(["critical", "high", "medium", "low"])
                predictions.append(
                    AIPrediction(
                        file_path=func.get("file", "unknown"),
                        function_name=func.get("function", "unknown"),
                        line_number=func.get("start_line", 1),
                        severity=severity,
                        confidence=round(random.uniform(0.6, 0.99), 2),
                        cwe_id=random.choice(["CWE-89", "CWE-79", "CWE-22", "CWE-78"]),
                        explanation=f"Mock {severity} vulnerability detected in {func.get('function', 'unknown')}.",
                        recommended_patch="Mock recommendation: validate all inputs.",
                        model_version=self.version,
                    )
                )

        return predictions

    def unload(self) -> None:
        logger.info("Mock AI model unloaded")
