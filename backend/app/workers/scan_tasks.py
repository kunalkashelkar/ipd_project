# ============================================================
# Scan Orchestration Tasks
# ============================================================

from __future__ import annotations

import asyncio

from celery import Task
from loguru import logger

from backend.app.workers.celery_app import celery_app
from backend.app.workers.preprocessing_tasks import run_preprocessing_task


class AsyncCeleryTask(Task):
    """Base class for running async code in Celery."""

    def __call__(self, *args, **kwargs):
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self.run(*args, **kwargs))


@celery_app.task(bind=True, base=AsyncCeleryTask, name="orchestrate_scan")
async def orchestrate_scan(self, scan_id: str):
    """Master workflow orchestrator for a scan.

    Triggers preprocessing, then AI inference, then results storage, then report.
    """
    logger.info("Starting orchestration for scan {scan_id}", scan_id=scan_id)

    # 1. Trigger Preprocessing
    # Using celery signature/chain for actual flow.
    # For MVP, we just call the next task.
    run_preprocessing_task.delay(scan_id)
