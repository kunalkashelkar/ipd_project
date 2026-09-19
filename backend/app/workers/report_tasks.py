# ============================================================
# Report Tasks (Phase 7)
# ============================================================

from __future__ import annotations

import uuid
from loguru import logger

from backend.app.database.session import AsyncSessionLocal
from backend.app.services.report_service import ReportService
from backend.app.workers.base_task import AsyncCeleryTask
from backend.app.workers.celery_app import celery_app


@celery_app.task(bind=True, base=AsyncCeleryTask, name="generate_report")
async def generate_report_task(self, report_id: str):
    """Generate report artifact asynchronously."""
    logger.info("Executing async report generation task for report {rid}", rid=report_id)

    async with AsyncSessionLocal() as session:
        try:
            service = ReportService(session)
            parsed_id = uuid.UUID(report_id)
            report = await service.execute_generation(parsed_id)
            logger.info(
                "Report {pid} generated successfully (format: {fmt}, type: {type})",
                pid=report.public_id,
                fmt=report.format,
                type=report.report_type,
            )
            return {"status": "completed", "report_id": str(report.id), "public_id": report.public_id}
        except Exception as exc:
            logger.error("Async report task failed for report {rid}: {err}", rid=report_id, err=exc)
            raise exc
