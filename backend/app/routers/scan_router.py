# ============================================================
# Scan Router — Scan Execution & Status
# ============================================================

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query

from backend.app.core.permissions import get_current_active_user, require_project_access
from backend.app.core.response import paginated_response, success_response
from backend.app.database.session import AsyncSession, get_db
from backend.app.schemas.scan import ScanCreate, ScanResponse, ScanStatusResponse
from backend.app.services.scan_service import ScanService

router = APIRouter(prefix="/scans", tags=["Scans"])


@router.post("", summary="Create and start a new scan")
async def create_scan(
    body: ScanCreate,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new scan and queue it for execution."""
    # Ensure user has access to the project
    await require_project_access(body.project_id, current_user, db)

    service = ScanService(db)
    scan = await service.create_scan(
        project_id=body.project_id,
        source_snapshot_id=body.source_snapshot_id,
        upload_id=body.upload_id,
        repository_id=body.repository_id,
        user_id=current_user.id,
    )
    return success_response(
        data=ScanResponse.model_validate(scan).model_dump(mode="json"),
        message="Scan created and queued successfully",
        status_code=201,
    )


@router.get("", summary="List scans")
async def list_scans(
    project_id: uuid.UUID | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List scans, optionally filtered by project.

    If project_id is provided, checks access. Otherwise, only admins
    can list all scans across the system.
    """
    if project_id:
        await require_project_access(project_id, current_user, db)
    elif current_user.role != "admin":
        from backend.app.core.exceptions import AuthorizationError
        raise AuthorizationError("Admin access required to list all scans")

    service = ScanService(db)
    scans, total = await service.list_scans(
        project_id=project_id, page=page, page_size=page_size
    )
    return paginated_response(
        items=[ScanResponse.model_validate(s).model_dump(mode="json") for s in scans],
        total=total,
        page=page,
        page_size=page_size,
        message="Scans retrieved successfully",
    )


@router.get("/{scan_id}", summary="Get scan details")
async def get_scan(
    scan_id: uuid.UUID,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get full details of a specific scan."""
    service = ScanService(db)
    scan = await service.get_scan(scan_id)

    # Check project access
    await require_project_access(scan.project_id, current_user, db)

    return success_response(
        data=ScanResponse.model_validate(scan).model_dump(mode="json"),
        message="Scan retrieved successfully",
    )


@router.get("/{scan_id}/status", summary="Get lightweight scan status")
async def get_scan_status(
    scan_id: uuid.UUID,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get just the status and progress for polling UI."""
    service = ScanService(db)
    scan = await service.get_scan_status(scan_id)

    # Check project access
    await require_project_access(scan.project_id, current_user, db)

    return success_response(
        data=ScanStatusResponse.model_validate(scan).model_dump(mode="json"),
        message="Scan status retrieved",
    )


@router.post("/{scan_id}/cancel", summary="Cancel a running scan")
async def cancel_scan(
    scan_id: uuid.UUID,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel an active scan."""
    service = ScanService(db)
    scan = await service.get_scan(scan_id)

    # Check project access
    await require_project_access(scan.project_id, current_user, db)

    await service.cancel_scan(scan_id, current_user.id)
    return success_response(message="Scan cancelled successfully")
