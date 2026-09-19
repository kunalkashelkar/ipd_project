# ============================================================
# Analytics Router (Phase 7)
# ============================================================

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query

from backend.app.core.authorization import (
    require_permission,
    require_project_access,
    resolve_organization_context,
)
from backend.app.core.response import success_response
from backend.app.database.session import AsyncSession, get_db
from backend.app.models.organization import Organization, OrganizationMember
from backend.app.models.project import Project
from backend.app.schemas.analytics import (
    AnalyticsMetricsResponse,
    DashboardResponse,
    ScanComparisonResponse,
)
from backend.app.services.analytics_service import AnalyticsService

router = APIRouter(tags=["Analytics"])


@router.get("/analytics/dashboard", summary="Get dashboard metrics")
async def get_dashboard(
    org_context: tuple[Organization, OrganizationMember] = Depends(resolve_organization_context),
    db: AsyncSession = Depends(get_db),
):
    """Get concise posture metrics for the main dashboard scoped to active organization."""
    org, _ = org_context
    service = AnalyticsService(db)
    metrics = await service.get_dashboard_metrics(
        organization_id=org.id,
    )
    return success_response(
        data=DashboardResponse.model_validate(metrics).model_dump(mode="json"),
        message="Dashboard metrics retrieved",
    )


@router.get("/analytics", summary="Get organization analytics")
async def get_organization_analytics(
    from_date: datetime | None = Query(None),
    to_date: datetime | None = Query(None),
    org_context: tuple[Organization, OrganizationMember] = Depends(resolve_organization_context),
    db: AsyncSession = Depends(get_db),
):
    """Get deep authoritative security analytics aggregated across the active organization."""
    org, _ = org_context
    service = AnalyticsService(db)
    metrics = await service.get_analytics_metrics(
        organization_id=org.id,
        from_date=from_date,
        to_date=to_date,
    )
    return success_response(
        data=AnalyticsMetricsResponse.model_validate(metrics).model_dump(mode="json"),
        message="Organization analytics retrieved",
    )


@router.get("/projects/{project_id}/analytics", summary="Get project analytics")
async def get_project_analytics(
    project_id: str,
    from_date: datetime | None = Query(None),
    to_date: datetime | None = Query(None),
    project_context: tuple[Project, OrganizationMember] = Depends(require_project_access),
    db: AsyncSession = Depends(get_db),
):
    """Get deep authoritative security analytics scoped to a specific project."""
    project, _ = project_context
    service = AnalyticsService(db)
    metrics = await service.get_analytics_metrics(
        organization_id=project.organization_id,
        project_id=project.id,
        from_date=from_date,
        to_date=to_date,
    )
    return success_response(
        data=AnalyticsMetricsResponse.model_validate(metrics).model_dump(mode="json"),
        message="Project analytics retrieved",
    )


@router.get("/projects/{project_id}/analytics/compare", summary="Compare two scans")
async def compare_scans(
    project_id: str,
    baseline_scan_id: str | None = Query(None),
    current_scan_id: str | None = Query(None),
    scan_a_id: str | None = Query(None),
    scan_b_id: str | None = Query(None),
    target_scan_id: str | None = Query(None),
    project_context: tuple[Project, OrganizationMember] = Depends(require_project_access),
    db: AsyncSession = Depends(get_db),
):
    """Perform authoritative scan-to-scan comparison distinguishing Existing, New, Fixed, Reopened."""
    from backend.app.core.exceptions import BadRequestError

    project, _ = project_context
    base_id = baseline_scan_id or scan_a_id
    curr_id = current_scan_id or scan_b_id or target_scan_id

    if not base_id or not curr_id:
        raise BadRequestError("Both baseline_scan_id and current_scan_id query parameters are required.")

    service = AnalyticsService(db)
    diff = await service.compare_scans(
        baseline_scan_id=base_id,
        current_scan_id=curr_id,
        org_id=project.organization_id,
        project_id=project.id,
    )
    return success_response(
        data=ScanComparisonResponse.model_validate(diff).model_dump(mode="json"),
        message="Scan comparison completed",
    )
