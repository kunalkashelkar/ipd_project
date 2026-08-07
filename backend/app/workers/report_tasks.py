# ============================================================
# Report Tasks
# ============================================================

from __future__ import annotations

from loguru import logger

from backend.app.workers.celery_app import celery_app
from backend.app.workers.scan_tasks import AsyncCeleryTask
from backend.app.workers.notification_tasks import send_notification_task


@celery_app.task(bind=True, base=AsyncCeleryTask, name="generate_report")
async def generate_report_task(self, scan_id: str):
    """Generate reports for a completed scan."""
    logger.info("Generating report for scan {scan_id}", scan_id=scan_id)

    # Note: Full report generation is built in Batch 3 report generator.
    # For now, we simulate success and trigger the notification.

    # 1. Generate JSON, CSV, PDF (simulated)
    # 2. Save report paths to DB
    # 3. Notify user
    send_notification_task.delay(scan_id, "scan_completed")

    logger.info("Report generation completed for scan {scan_id}", scan_id=scan_id)
