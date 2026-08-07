# ============================================================
# Celery Application Configuration
# ============================================================

from __future__ import annotations

from celery import Celery

from backend.app.core.config import get_settings

settings = get_settings()

# Initialize Celery App
celery_app = Celery(
    "vulnscan",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "backend.app.workers.scan_tasks",
        "backend.app.workers.preprocessing_tasks",
        "backend.app.workers.ai_tasks",
        "backend.app.workers.report_tasks",
        "backend.app.workers.notification_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Configure task routing based on queues
    task_routes={
        "backend.app.workers.ai_tasks.*": {"queue": "ai_queue"},
        "backend.app.workers.scan_tasks.*": {"queue": "default_queue"},
        "backend.app.workers.preprocessing_tasks.*": {"queue": "default_queue"},
        "backend.app.workers.report_tasks.*": {"queue": "default_queue"},
        "backend.app.workers.notification_tasks.*": {"queue": "default_queue"},
    },
)
