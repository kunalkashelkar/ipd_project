# ============================================================
# Result Router — Vulnerability Findings
# ============================================================

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.app.core.authorization import (
    get_current_user,
    require_scan_access,
)
from backend.app.core.exceptions import AuthorizationError, NotFoundError
from backend.app.core.response import paginated_response, success_response
from backend.app.database.session import AsyncSession, get_db
from backend.app.models.organization import Organization, OrganizationMember
from backend.app.models.project import Project
from backend.app.models.rbac import Role, RolePermission
from backend.app.models.scan import Scan
from backend.app.models.scan_result import ScanResult
from backend.app.models.user import User
from backend.app.schemas.result import FeedbackCreate, FeedbackResponse, ScanResultResponse
from backend.app.services.result_service import ResultService

router = APIRouter(prefix="/results", tags=["Results"])


@router.get("/scans/{scan_id}", summary="Get paginated scan results")
async def get_scan_results(
    scan_id: uuid.UUID,
    severity: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    scan_context: tuple[Scan, Project, OrganizationMember] = Depends(require_scan_access),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all vulnerability findings for a specific scan."""
    _, _, member = scan_context

    if member.role.name != "owner":
        granted = {rp.permission.key for rp in member.role.permissions if rp.permission}
        if "finding.read" not in granted:
            raise AuthorizationError("Permission denied: Action requires 'finding.read'")

    service = ResultService(db)
    results, total = await service.get_scan_results(
        scan_id=scan_id,
        user_id=current_user.id,
        role=member.role.name,
        page=page,
        page_size=page_size,
        severity=severity,
    )
    return paginated_response(
        items=[ScanResultResponse.model_validate(r).model_dump(mode="json") for r in results],
        total=total,
        page=page,
        page_size=page_size,
        message="Results retrieved successfully",
    )


@router.get("/scans/{scan_id}/summary", summary="Get scan results summary")
async def get_scan_summary(
    scan_id: uuid.UUID,
    scan_context: tuple[Scan, Project, OrganizationMember] = Depends(require_scan_access),
    db: AsyncSession = Depends(get_db),
):
    """Get aggregated vulnerability statistics for a scan."""
    _, _, member = scan_context

    if member.role.name != "owner":
        granted = {rp.permission.key for rp in member.role.permissions if rp.permission}
        if "finding.read" not in granted:
            raise AuthorizationError("Permission denied: Action requires 'finding.read'")

    service = ResultService(db)
    summary = await service.get_scan_summary(scan_id)
    return success_response(
        data=summary,
        message="Scan summary retrieved successfully",
    )


@router.post("/{result_id}/feedback", summary="Submit feedback on a result")
async def submit_feedback(
    result_id: uuid.UUID,
    body: FeedbackCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit human feedback (correct/incorrect) on an AI prediction."""
    stmt = (
        select(ScanResult, OrganizationMember)
        .join(Scan, ScanResult.scan_id == Scan.id)
        .join(Project, Scan.project_id == Project.id)
        .join(Organization, Project.organization_id == Organization.id)
        .join(
            OrganizationMember,
            (OrganizationMember.organization_id == Organization.id)
            & (OrganizationMember.user_id == current_user.id)
            & (OrganizationMember.status == "active"),
        )
        .options(
            selectinload(OrganizationMember.role)
            .selectinload(Role.permissions)
            .selectinload(RolePermission.permission)
        )
        .where(ScanResult.id == result_id)
    )
    res = await db.execute(stmt)
    row = res.first()
    if row is None:
        raise NotFoundError("Result not found")

    _, member = row
    if member.role.name != "owner":
        granted = {rp.permission.key for rp in member.role.permissions if rp.permission}
        if "finding.read" not in granted and "finding.update" not in granted:
            raise AuthorizationError("Permission denied: Action requires 'finding.read' or 'finding.update'")

    service = ResultService(db)
    feedback = await service.submit_feedback(
        result_id=result_id,
        user_id=current_user.id,
        is_correct=body.is_correct,
        comment=body.comment,
    )
    return success_response(
        data=FeedbackResponse.model_validate(feedback).model_dump(mode="json"),
        message="Feedback submitted successfully",
        status_code=201,
    )
