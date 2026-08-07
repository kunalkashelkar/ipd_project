# ============================================================
# Report Router — Exporting Scan Results
# ============================================================

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query

from backend.app.core.permissions import get_current_active_user
from backend.app.core.response import paginated_response, success_response
from backend.app.database.session import AsyncSession, get_db
from backend.app.schemas.report import ReportCreate, ReportResponse
from backend.app.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/scans/{scan_id}", summary="Get reports for a scan")
async def get_scan_reports(
    scan_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List all reports generated for a specific scan."""
    service = ReportService(db)
    reports, total = await service.get_scan_reports(
        scan_id=scan_id,
        page=page,
        page_size=page_size,
    )
    return paginated_response(
        items=[ReportResponse.model_validate(r).model_dump(mode="json") for r in reports],
        total=total,
        page=page,
        page_size=page_size,
        message="Reports retrieved successfully",
    )


@router.post("", summary="Request a new report")
async def request_report(
    body: ReportCreate,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger report generation for a scan in a specific format."""
    service = ReportService(db)
    report = await service.request_report(
        scan_id=body.scan_id,
        format=body.format,
        user_id=current_user.id,
    )
    return success_response(
        data=ReportResponse.model_validate(report).model_dump(mode="json"),
        message="Report generation requested",
        status_code=202,
    )
