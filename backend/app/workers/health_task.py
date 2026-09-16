# ============================================================
# Celery Infrastructure Health Check Task
# ============================================================
# Dedicated task to verify Celery broker/worker execution and Redis
# result backend without simulating any scan or vulnerability detection.
# ============================================================

from __future__ import annotations

from datetime import datetime, timezone
from backend.app.workers.celery_app import celery_app
from backend.app.core.logging import logger


@celery_app.task(name="infrastructure_ping", bind=True)
def ping_infrastructure(self, echo_message: str = "pong") -> dict:
    """Infrastructure ping task solely proving Celery worker and Redis wiring."""
    logger.info("Executing infrastructure_ping task: {msg}", msg=echo_message)
    return {
        "status": "ok",
        "task_id": self.request.id,
        "echo": echo_message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "worker": self.request.hostname,
    }
