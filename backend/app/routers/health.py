# ============================================================
# Health & Status Router
# ============================================================

from __future__ import annotations

import time

from fastapi import APIRouter

from backend.app.config import get_settings
from backend.app.schemas import HealthResponse, StatusResponse

router = APIRouter(tags=["System"])

# Track application start time
_start_time = time.time()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Returns the health status of the API.",
)
async def health_check() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        version="0.1.0",
        environment=settings.app_env,
    )


@router.get(
    "/status",
    response_model=StatusResponse,
    summary="System status",
    description="Returns the system status including database connectivity and uptime.",
)
async def system_status() -> StatusResponse:
    uptime = time.time() - _start_time
    return StatusResponse(
        status="ok",
        database="connected",  # Placeholder — Phase 2 will do a real DB ping
        uptime_seconds=round(uptime, 2),
    )
