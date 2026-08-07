# ============================================================
# AI Predictor Service
# ============================================================

from __future__ import annotations

from backend.app.ai.contracts import AIInferenceRequest, AIPrediction
from backend.app.ai.loader import AILoader
from backend.app.core.logging import logger


class AIPredictor:
    """Wrapper that handles execution of the loaded AI model."""

    def __init__(self):
        # Retrieve the singleton model (loads into memory if first time)
        self.model = AILoader.get_model()

    def run_inference(self, scan_id: str, language: str, functions: list[dict]) -> list[AIPrediction]:
        """Execute the model on the preprocessed functions."""
        request = AIInferenceRequest(
            scan_id=scan_id,
            language=language,
            functions=functions,
        )

        logger.info(
            "Executing AI inference (engine={version}) on scan {scan_id}",
            version=self.model.version,
            scan_id=scan_id,
        )

        # The backend does not care HOW this predict method works.
        # It just passes the request contract and gets back prediction contracts.
        predictions = self.model.predict(request)

        logger.info(
            "AI inference complete for scan {scan_id}. Found {count} potential vulnerabilities.",
            scan_id=scan_id,
            count=len(predictions),
        )

        return predictions
