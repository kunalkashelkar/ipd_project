# ============================================================
# Snapshot Preprocessing Celery Tasks (Phase 3 Worker Isolation)
# ============================================================

from __future__ import annotations

import asyncio
import uuid

from loguru import logger

from backend.app.database.session import async_session_factory
from backend.app.services.preprocessing_service import PreprocessingService
from backend.app.workers.base_task import AsyncCeleryTask
from backend.app.workers.celery_app import celery_app


@celery_app.task(bind=True, base=AsyncCeleryTask, name="process_source_snapshot")
async def process_source_snapshot_task(
    self,
    snapshot_id: str,
    org_id: str,
    project_id: str,
):
    """Worker task that isolates archive extraction, parsing, and preprocessing."""
    logger.info("Starting processing task for snapshot {id}", id=snapshot_id)

    async with async_session_factory() as db:
        service = PreprocessingService()
        result = await service.process_snapshot(
            db=db,
            snapshot_id=uuid.UUID(snapshot_id),
            org_id=uuid.UUID(org_id),
            project_id=uuid.UUID(project_id),
        )

        logger.info(
            "Snapshot {id} processing finished with status: {status}",
            id=snapshot_id,
            status=result.status,
        )
        return {
            "snapshot_id": snapshot_id,
            "status": result.status,
            "file_count": result.file_count,
            "function_count": result.function_count,
            "duplicate_count": result.duplicate_count,
        }
