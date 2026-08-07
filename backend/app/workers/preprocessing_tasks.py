# ============================================================
# Preprocessing Tasks
# ============================================================

from __future__ import annotations

import asyncio
import uuid

from loguru import logger

from backend.app.core.config import get_settings
from backend.app.database.session import async_session_factory
from backend.app.repositories.scan_repository import ScanRepository
from backend.app.repositories.upload_repository import UploadRepository
from backend.app.services.preprocessing_service import PreprocessingService
from backend.app.workers.ai_tasks import run_ai_inference_task
from backend.app.workers.celery_app import celery_app
from backend.app.workers.scan_tasks import AsyncCeleryTask


@celery_app.task(bind=True, base=AsyncCeleryTask, name="run_preprocessing")
async def run_preprocessing_task(self, scan_id: str):
    """Run preprocessing on the upload associated with a scan."""
    logger.info("Running preprocessing for scan {scan_id}", scan_id=scan_id)

    async with async_session_factory() as db:
        scan_repo = ScanRepository(db)
        upload_repo = UploadRepository(db)

        scan = await scan_repo.get_by_id(uuid.UUID(scan_id))
        if not scan:
            logger.error("Scan {scan_id} not found", scan_id=scan_id)
            return

        if not scan.upload_id:
            logger.error("Scan {scan_id} has no associated upload", scan_id=scan_id)
            return

        upload = await upload_repo.get_by_id(scan.upload_id)
        if not upload:
            logger.error("Upload {upload_id} not found", upload_id=scan.upload_id)
            return

        # Update status
        await scan_repo.update_status(
            scan.id, status="preprocessing", progress=10.0, current_stage="Extracting and parsing files"
        )
        await db.commit()

        # Run preprocessing
        preprocessor = PreprocessingService()
        try:
            result = preprocessor.process_upload(upload.stored_path, str(upload.id))

            # Trigger AI Inference
            run_ai_inference_task.delay(scan_id, result.model_dump(mode="json"))
        except Exception as exc:
            logger.exception("Preprocessing failed for scan {scan_id}: {exc}", scan_id=scan_id, exc=str(exc))
            await scan_repo.update_status(
                scan.id, status="failed", error_message=f"Preprocessing failed: {str(exc)}"
            )
            await db.commit()
