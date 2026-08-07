# ============================================================
# AI Inference Tasks
# ============================================================

from __future__ import annotations

import asyncio
import uuid

from loguru import logger

from backend.app.ai.predictor import AIPredictor
from backend.app.database.session import async_session_factory
from backend.app.repositories.scan_repository import ScanRepository
from backend.app.repositories.result_repository import ResultRepository
from backend.app.workers.celery_app import celery_app
from backend.app.workers.scan_tasks import AsyncCeleryTask
from backend.app.workers.report_tasks import generate_report_task


@celery_app.task(bind=True, base=AsyncCeleryTask, name="run_ai_inference")
async def run_ai_inference_task(self, scan_id: str, preprocessing_result: dict):
    """Run AI inference on the preprocessed code."""
    logger.info("Running AI inference for scan {scan_id}", scan_id=scan_id)

    async with async_session_factory() as db:
        scan_repo = ScanRepository(db)
        result_repo = ResultRepository(db)

        scan = await scan_repo.get_by_id(uuid.UUID(scan_id))
        if not scan:
            logger.error("Scan {scan_id} not found", scan_id=scan_id)
            return

        # Update status
        await scan_repo.update_status(
            scan.id, status="ai_running", progress=50.0, current_stage="Analyzing code for vulnerabilities"
        )
        await db.commit()

        try:
            # 1. Run inference
            predictor = AIPredictor()
            predictions = predictor.run_inference(
                scan_id=scan_id,
                language=preprocessing_result.get("language", "unknown"),
                functions=preprocessing_result.get("files", []),
            )

            # 2. Store results
            await scan_repo.update_status(
                scan.id, status="storing_results", progress=90.0, current_stage="Saving findings"
            )
            await db.commit()

            # Bulk insert predictions
            if predictions:
                result_dicts = []
                for p in predictions:
                    result_dicts.append({
                        "scan_id": scan.id,
                        "file_path": p.file_path,
                        "function_name": p.function_name,
                        "line_number": p.line_number,
                        "severity": p.severity,
                        "confidence": p.confidence,
                        "cwe_id": p.cwe_id,
                        "explanation": p.explanation,
                        "recommended_patch": p.recommended_patch,
                        "model_version": p.model_version,
                        "raw_prediction_json": p.model_dump(mode="json"),
                    })
                await result_repo.bulk_create(result_dicts)
                await db.commit()

            # 3. Mark scan completed
            await scan_repo.update_status(
                scan.id, status="completed", progress=100.0, current_stage="Finished"
            )
            await db.commit()

            logger.info("Scan {scan_id} completed successfully", scan_id=scan_id)

            # 4. Trigger Report Generation
            generate_report_task.delay(scan_id)

        except Exception as exc:
            logger.exception("AI Inference failed for scan {scan_id}: {exc}", scan_id=scan_id, exc=str(exc))
            await scan_repo.update_status(
                scan.id, status="failed", error_message=f"AI Inference failed: {str(exc)}"
            )
            await db.commit()
