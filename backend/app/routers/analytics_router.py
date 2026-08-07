# ============================================================
# Analytics Router
# ============================================================

from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.app.core.permissions import get_current_active_user
from backend.app.core.response import success_response
from backend.app.database.session import AsyncSession, get_db
from backend.app.schemas.analytics import DashboardResponse
from backend.app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/dashboard", summary="Get dashboard metrics")
async def get_dashboard(
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get high-level metrics for the main dashboard."""
    service = AnalyticsService(db)
    metrics = await service.get_dashboard_metrics(
        user_id=current_user.id,
        role=current_user.role,
    )
    return success_response(
        data=DashboardResponse.model_validate(metrics).model_dump(mode="json"),
        message="Dashboard metrics retrieved",
    )
