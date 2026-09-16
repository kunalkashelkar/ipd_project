# ============================================================
# Health Router — Liveness & Readiness Checks
# ============================================================

from __future__ import annotations

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
    """Verify runtime dependencies (PostgreSQL and Redis).

    Returns 200 if all required services respond, or 503 if any dependency fails.
    """
    settings = get_settings()
    db_status = "disconnected"
    redis_status = "unavailable"

    # 1. Check PostgreSQL
    try:
        from backend.app.database.session import engine
        from sqlalchemy import text

        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            db_status = "connected"
    except Exception:
        db_status = "disconnected"

    # 2. Check Redis
    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url(settings.redis_url, socket_connect_timeout=2)
        await r.ping()
        redis_status = "connected"
        await r.aclose()
    except Exception:
        redis_status = "unavailable"

    is_ready = (db_status == "connected") and (redis_status == "connected")

    payload = {
        "status": "success" if is_ready else "error",
        "data": {
            "database": db_status,
            "redis": redis_status,
            "ready": is_ready,
        },
        "message": "Service is ready" if is_ready else "Service dependencies unavailable",
    }

    status_code = status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(status_code=status_code, content=payload)
