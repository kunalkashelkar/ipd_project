# ============================================================
# Report Router — Exporting Scan Results (Phase 7)
# ============================================================

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Response, status
from fastapi.responses import StreamingResponse
import io

from backend.app.core.authorization import (
    get_current_user,
    require_permission,
    require_scan_access,
    resolve_organization_context,
)
from backend.app.core.rate_limit import RateLimiter
from backend.app.core.response import paginated_response, success_response
from backend.app.database.session import AsyncSession, get_db
from backend.app.models.organization import Organization, OrganizationMember
from backend.app.models.project import Project
from backend.app.models.scan import Scan
from backend.app.models.user import User
from backend.app.schemas.report import ReportCreate, ReportResponse
from backend.app.services.audit_service import AuditService
from backend.app.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["Reports"])


def _verify_report_read(member: OrganizationMember) -> None:
    if member.role.name == "owner":
        return
    granted = {rp.permission.key for rp in member.role.permissions if rp.permission}
    if "report.read" not in granted:
        raise AuthorizationError("Permission denied: Action requires 'report.read'")


def _verify_report_create(member: OrganizationMember) -> None:
    if member.role.name == "owner":
        return
    granted = {rp.permission.key for rp in member.role.permissions if rp.permission}
    if "report.create" not in granted:
        raise AuthorizationError("Permission denied: Action requires 'report.create'")


@router.get("", summary="List reports for active organization")
async def list_reports(
    project_id: str | None = Query(None),
    scan_id: str | None = Query(None),
    report_type: str | None = Query(None),
    format: str | None = Query(None),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    org_context: tuple[Organization, OrganizationMember] = Depends(resolve_organization_context),
    db: AsyncSession = Depends(get_db),
):
    """List paginated reports scoped to the active organization."""
    org, member = org_context
    _verify_report_read(member)

    # Resolve public project_id and scan_id if passed
    resolved_proj_id = None
    if project_id:
        from backend.app.repositories.project_repository import ProjectRepository
        p = await ProjectRepository(db).get_by_id_or_public_id(project_id)
        resolved_proj_id = p.id if p else None

    resolved_scan_id = None
    if scan_id:
        from backend.app.repositories.scan_repository import ScanRepository
        s = await ScanRepository(db).get_by_id_or_public_id(scan_id)
        resolved_scan_id = s.id if s else None

    service = ReportService(db)
    reports, total = await service.list_reports(
        org_id=org.id,
        project_id=resolved_proj_id,
        scan_id=resolved_scan_id,
        report_type=report_type,
        format=format,
        status=status,
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


@router.get("/scans/{scan_id}", summary="Get reports for a scan")
async def get_scan_reports(
    scan_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    scan_context: tuple[Scan, Project, OrganizationMember] = Depends(require_scan_access),
    db: AsyncSession = Depends(get_db),
):
    """List all reports generated for a specific scan."""
    _, _, member = scan_context
    _verify_report_read(member)

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


@router.post(
    "",
    summary="Request a new report",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(RateLimiter(times=20, seconds=60, scope="reports:create"))],
)
async def request_report(
    body: ReportCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger report generation for a scan in a specific format asynchronously."""
    scan, project, member = await require_scan_access(body.scan_id, current_user, db)
    _verify_report_create(member)

    service = ReportService(db)
    report = await service.request_report(
        scan_id=scan.id,
        format=body.format,
        report_type=body.report_type,
        user_id=current_user.id,
        org_id=project.organization_id,
        config=body.config,
    )
    return success_response(
        data=ReportResponse.model_validate(report).model_dump(mode="json"),
        message="Report generation queued",
        status_code=202,
    )


@router.get("/{report_id}", summary="Get report details")
async def get_report_detail(
    report_id: str,
    org_context: tuple[Organization, OrganizationMember] = Depends(resolve_organization_context),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve details and status for a specific report."""
    org, member = org_context
    _verify_report_read(member)

    service = ReportService(db)
    report = await service.get_report(report_id, org.id)
    return success_response(
        data=ReportResponse.model_validate(report).model_dump(mode="json"),
        message="Report retrieved successfully",
    )


@router.get("/{report_id}/download", summary="Download completed report file")
async def download_report(
    report_id: str,
    org_context: tuple[Organization, OrganizationMember] = Depends(resolve_organization_context),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Securely stream completed report content."""
    org, member = org_context
    _verify_report_read(member)

    service = ReportService(db)
    content_bytes, filename, content_type = await service.get_report_download(report_id, org.id)

    audit = AuditService(db)
    await audit.log(
        user_id=current_user.id,
        action="report.downloaded",
        resource_type="report",
        resource_id=str(report_id),
        metadata={"filename": filename},
    )

    return StreamingResponse(
        io.BytesIO(content_bytes),
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(content_bytes)),
        },
    )


@router.post("/{report_id}/retry", summary="Retry failed report generation", status_code=202)
async def retry_report(
    report_id: str,
    org_context: tuple[Organization, OrganizationMember] = Depends(resolve_organization_context),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retry an asynchronous report generation task if it previously failed."""
    org, member = org_context
    _verify_report_create(member)

    service = ReportService(db)
    report = await service.get_report(report_id, org.id)
    report.status = "queued"
    report.error_message = None
    await db.commit()

    from backend.app.workers.report_tasks import generate_report_task
    generate_report_task.delay(str(report.id))

    return success_response(
        data=ReportResponse.model_validate(report).model_dump(mode="json"),
        message="Report generation retried",
        status_code=202,
    )
