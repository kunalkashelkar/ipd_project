# ============================================================
# Celery Application Configuration
# ============================================================

from __future__ import annotations

from celery import Celery

from backend.app.core.config import get_settings

settings = get_settings()

broker_url = settings.celery_broker_url or settings.redis_url
result_backend = settings.celery_result_backend or settings.redis_url

# Initialize Celery App
celery_app = Celery(
    "vulnscan",
    broker=broker_url,
    backend=result_backend,
    include=[
        "backend.app.workers.health_task",
        "backend.app.workers.scan_tasks",
        "backend.app.workers.preprocessing_tasks",
        "backend.app.workers.snapshot_tasks",
        "backend.app.workers.repository_tasks",
        "backend.app.workers.ai_tasks",
        "backend.app.workers.report_tasks",
        "backend.app.workers.notification_tasks",
        "backend.app.workers.remediation_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_default_queue="default_queue",
    # Configure task routing based on queues
    task_routes={
        "backend.app.workers.health_task.*": {"queue": "default_queue"},
        "backend.app.workers.ai_tasks.*": {"queue": "ai_queue"},
        "backend.app.workers.scan_tasks.*": {"queue": "default_queue"},
        "backend.app.workers.preprocessing_tasks.*": {"queue": "default_queue"},
        "backend.app.workers.snapshot_tasks.*": {"queue": "default_queue"},
        "backend.app.workers.repository_tasks.*": {"queue": "default_queue"},
        "backend.app.workers.report_tasks.*": {"queue": "default_queue"},
        "backend.app.workers.notification_tasks.*": {"queue": "default_queue"},
        "process_source_snapshot": {"queue": "default_queue"},
        "sync_repository": {"queue": "default_queue"},
        "run_ai_inference": {"queue": "ai_queue"},
    },
)
