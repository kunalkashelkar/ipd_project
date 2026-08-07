# ============================================================
# Health Router — Health, Readiness, Liveness
# ============================================================

from __future__ import annotations

from fastapi import APIRouter

from backend.app.core.config import get_settings
from backend.app.core.response import success_response

router = APIRouter(tags=["System"])


@router.get("/health", summary="Health check")
async def health_check():
    """Basic health check — returns app info."""
    settings = get_settings()
    return success_response(
        data={
            "app": settings.app_name,
            "version": "0.1.0",
            "environment": settings.app_env,
            "database": "unknown",
            "redis": "unknown",
        },
        message="Service is healthy",
    )


@router.get("/health/ready", summary="Readiness check")
async def readiness_check():
    """Check if the service is ready to accept traffic.

    Verifies database connectivity.
    """
    db_status = "unknown"
    try:
        from backend.app.database.session import engine

        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
            db_status = "connected"
    except Exception:
        db_status = "disconnected"

    redis_status = "unknown"
    try:
        import redis.asyncio as aioredis

        settings = get_settings()
        r = aioredis.from_url(settings.redis_url)
        await r.ping()
        redis_status = "connected"
        await r.close()
    except Exception:
        redis_status = "unavailable"

    is_ready = db_status == "connected"
    return success_response(
        data={
            "database": db_status,
            "redis": redis_status,
            "ready": is_ready,
        },
        message="Service is ready" if is_ready else "Service is not ready",
    )


@router.get("/health/live", summary="Liveness check")
async def liveness_check():
    """Simple liveness probe — always returns success."""
    return success_response(
        data={"alive": True},
        message="Service is alive",
    )
