# ============================================================
# Notification Tasks
# ============================================================

from __future__ import annotations

import uuid

from loguru import logger

from backend.app.database.session import async_session_factory
from backend.app.repositories.scan_repository import ScanRepository
from backend.app.repositories.notification_repository import NotificationRepository
from backend.app.workers.celery_app import celery_app
from backend.app.workers.base_task import AsyncCeleryTask


@celery_app.task(bind=True, base=AsyncCeleryTask, name="send_notification")
async def send_notification_task(self, scan_id: str, notification_type: str):
    """Send an in-app notification to the user."""
    logger.info("Sending {type} notification for scan {scan_id}", type=notification_type, scan_id=scan_id)

    async with async_session_factory() as db:
        scan_repo = ScanRepository(db)
        notif_repo = NotificationRepository(db)

        scan = await scan_repo.get_by_id(uuid.UUID(scan_id))
        if not scan or not scan.created_by:
            return

        title = "Scan Completed" if notification_type == "scan_completed" else "Scan Failed"
        body = f"Scan for project has finished with status: {scan.status}"

        await notif_repo.create(
            user_id=scan.created_by,
            type=notification_type,
            title=title,
            body=body,
            entity_type="scan",
            entity_id=scan.id,
            is_read=False,
        )
        await db.commit()

    # Note: In Batch 4, we will also push this via WebSockets here.
