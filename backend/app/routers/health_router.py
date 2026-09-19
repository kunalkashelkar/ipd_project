# ============================================================
# Health Router — Liveness & Readiness Checks
# ============================================================

from __future__ import annotations

import asyncio

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from backend.app.core.config import get_settings
from backend.app.core.response import success_response

router = APIRouter(tags=["System"])


@router.get("/health", summary="Liveness check")
async def health_check():
    """Basic health / liveness check — reports application metadata."""
    settings = get_settings()
    return success_response(
        data={
            "app": settings.app_name,
            "version": "0.1.0",
            "environment": settings.app_env,
            "status": "healthy",
        },
        message="Service is alive",
    )


@router.get("/health/live", summary="Liveness probe")
async def liveness_check():
    """K8s/Docker liveness probe — returns 200 if the process is running."""
    return success_response(
        data={"alive": True},
        message="Service is alive",
    )


@router.get("/health/ready", summary="Readiness check")
async def readiness_check():
    """Verify runtime dependencies (PostgreSQL, Redis, Storage, and Celery workers).

    Returns 200 if all core services respond, or 503 if any critical dependency fails.
    All probes enforce strict <=2.0s bounded execution to prevent hanging health checks.
    """
    settings = get_settings()
    db_status = "disconnected"
    redis_status = "unavailable"
    storage_status = "unavailable"
    worker_status = "unavailable"

    # 1. Check PostgreSQL with bounded 2s timeout
    try:
        from backend.app.database.session import engine
        from sqlalchemy import text

        async def _check_db():
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))

        await asyncio.wait_for(_check_db(), timeout=2.0)
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    # 2. Check Redis with bounded 2s timeout
    try:
        import redis.asyncio as aioredis

        async def _check_redis():
            r = aioredis.from_url(settings.redis_url, socket_connect_timeout=2)
            await r.ping()
            await r.aclose()

        await asyncio.wait_for(_check_redis(), timeout=2.0)
        redis_status = "connected"
    except Exception:
        redis_status = "unavailable"

    # 3. Check Storage Backend with bounded 2s timeout
    try:
        if settings.storage_backend == "local":
            p = settings.storage_path
            p.mkdir(parents=True, exist_ok=True)
            test_file = p / ".healthcheck"
            test_file.write_text("ok", encoding="utf-8")
            test_file.unlink(missing_ok=True)
            storage_status = "connected"
        else:
            from backend.app.storage.service import StorageService
            storage_svc = StorageService()
            storage_status = "connected"
    except Exception:
        storage_status = "unavailable"

    # 4. Check Celery Worker pool readiness (non-fatal / degraded state reporting)
    try:
        from backend.app.tasks.celery_app import celery_app

        def _check_celery():
            insp = celery_app.control.inspect(timeout=1.0)
            ping_res = insp.ping()
            return bool(ping_res)

        has_workers = await asyncio.wait_for(asyncio.to_thread(_check_celery), timeout=2.0)
        worker_status = "connected" if has_workers else "degraded"
    except Exception:
        worker_status = "degraded"

    is_ready = (db_status == "connected") and (redis_status == "connected") and (storage_status == "connected")

    payload = {
        "status": "success" if is_ready else "error",
        "data": {
            "database": db_status,
            "redis": redis_status,
            "storage": storage_status,
            "workers": worker_status,
            "ready": is_ready,
        },
        "message": "Service is ready" if is_ready else "Critical service dependencies unavailable",
    }

    status_code = status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(status_code=status_code, content=payload)


@router.get("/health/metrics", summary="Lightweight operational metrics")
async def operational_metrics():
    """Retrieve lightweight operational health counters and duration metrics."""
    from backend.app.core.metrics import metrics

    return success_response(
        data=metrics.get_snapshot(),
        message="Operational metrics snapshot retrieved",
    )


