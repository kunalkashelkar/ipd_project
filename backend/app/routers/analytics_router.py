# ============================================================
# Analytics Router
# ============================================================

from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.app.core.authorization import resolve_organization_context
from backend.app.core.response import success_response
from backend.app.database.session import AsyncSession, get_db
from backend.app.models.organization import Organization, OrganizationMember
from backend.app.schemas.analytics import DashboardResponse
from backend.app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/dashboard", summary="Get dashboard metrics")
async def get_dashboard(
    org_context: tuple[Organization, OrganizationMember] = Depends(resolve_organization_context),
    db: AsyncSession = Depends(get_db),
):
    """Get high-level metrics for the main dashboard scoped to active organization."""
    org, member = org_context
    service = AnalyticsService(db)
    metrics = await service.get_dashboard_metrics(
        organization_id=org.id,
    )
    return success_response(
        data=DashboardResponse.model_validate(metrics).model_dump(mode="json"),
        message="Dashboard metrics retrieved",
    )
