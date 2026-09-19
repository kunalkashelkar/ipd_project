# ============================================================
# Scan Router — Phase 4 Scan Execution, Lifecycle & Artifacts
# ============================================================

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import Response
from sqlalchemy import select

from backend.app.core.authorization import (
    get_current_user,
    require_permission,
    require_project_access,
    require_scan_access,
)
from backend.app.core.rate_limit import RateLimiter
from backend.app.core.response import paginated_response, success_response
from backend.app.database.session import AsyncSession, get_db
from backend.app.models.analysis_artifact import AnalysisArtifact
from backend.app.models.organization import Organization, OrganizationMember
from backend.app.models.project import Project
from backend.app.models.scan import Scan
from backend.app.models.user import User
from backend.app.schemas.scan import (
    AnalysisArtifactResponse,
    ScanCreate,
    ScanResponse,
    ScanStageRunResponse,
    ScanStatusResponse,
)
from backend.app.services.scan_service import ScanService

router = APIRouter(prefix="/scans", tags=["Scans"])


@router.post(
    "",
    summary="Create and start a new scan",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RateLimiter(times=30, seconds=60, scope="scans:create"))],
)
async def create_scan(
    body: ScanCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new scan and queue it for execution.

    Requires access to project, validates immutable snapshot, and enforces scan.create permission.
    """
    project, member = await require_project_access(body.project_id, current_user, db)

    # Enforce scan.create permission on member role
    if member.role.name != "owner":
        granted = {rp.permission.key for rp in member.role.permissions if rp.permission}
        if "scan.create" not in granted:
            raise AuthorizationError("Permission denied: Action requires 'scan.create'")

    service = ScanService(db)
    scan = await service.create_scan(
        project_id=body.project_id,
        source_snapshot_id=body.source_snapshot_id,
        upload_id=body.upload_id,
        repository_id=body.repository_id,
        user_id=current_user.id,
        idempotency_key=body.idempotency_key,
        config=body.config,
    )
    return success_response(
        data=ScanResponse.model_validate(scan).model_dump(mode="json"),
        message="Scan created and queued successfully",
        status_code=201,
    )


@router.get("", summary="List scans")
async def list_scans(
    project_id: str | None = Query(None),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    org_context: tuple[Organization, OrganizationMember] = Depends(require_permission("scan.read")),
    db: AsyncSession = Depends(get_db),
):
    """List scans accessible to the authenticated user strictly scoped to the active organization."""
    org, _ = org_context

    resolved_project_id: uuid.UUID | None = None
    if project_id:
        from backend.app.core.identifiers import is_valid_uuid
        from sqlalchemy import or_
        pid_str = str(project_id).strip()
        if is_valid_uuid(pid_str):
            cond = or_(Project.id == uuid.UUID(pid_str), Project.public_id == pid_str)
        else:
            cond = (Project.public_id == pid_str)

        stmt = select(Project).where(cond, Project.organization_id == org.id)
        res = await db.execute(stmt)
        proj = res.scalar_one_or_none()
        if proj is None:
            raise NotFoundError("Project not found")
        resolved_project_id = proj.id

    service = ScanService(db)
    scans, total = await service.list_scans(
        project_id=resolved_project_id,
        organization_id=org.id,
        status=status,
        page=page,
        page_size=page_size,
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
    scan_id: str,
    scan_context: tuple[Scan, Project, OrganizationMember] = Depends(require_scan_access),
    db: AsyncSession = Depends(get_db),
):
    """Get full details of a specific scan ensuring tenant isolation."""
    scan, _, _ = scan_context
    service = ScanService(db)
    scan_detail = await service.get_scan(scan.id)

    return success_response(
        data=ScanResponse.model_validate(scan_detail).model_dump(mode="json"),
        message="Scan retrieved successfully",
    )


@router.get("/{scan_id}/status", summary="Get lightweight scan status")
async def get_scan_status(
    scan_id: str,
    scan_context: tuple[Scan, Project, OrganizationMember] = Depends(require_scan_access),
    db: AsyncSession = Depends(get_db),
):
    """Get status and progress for UI polling."""
    scan, _, _ = scan_context
    return success_response(
        data=ScanStatusResponse.model_validate(scan).model_dump(mode="json"),
        message="Scan status retrieved",
    )


@router.get("/{scan_id}/stages", summary="Get scan execution stage runs")
async def get_scan_stages(
    scan_id: str,
    scan_context: tuple[Scan, Project, OrganizationMember] = Depends(require_scan_access),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve history of all stage executions for a scan."""
    scan, _, _ = scan_context
    service = ScanService(db)
    stages = await service.get_scan_stages(scan.id)
    return success_response(
        data=[ScanStageRunResponse.model_validate(s).model_dump(mode="json") for s in stages],
        message="Scan stage runs retrieved",
    )


@router.get("/{scan_id}/artifacts", summary="List static analysis graph artifacts")
async def get_scan_artifacts(
    scan_id: str,
    scan_context: tuple[Scan, Project, OrganizationMember] = Depends(require_scan_access),
    db: AsyncSession = Depends(get_db),
):
    """List canonical graph and analysis artifacts (AST, CFG, PDG, CPG, CALL_GRAPH, TAINT)."""
    scan, _, _ = scan_context
    service = ScanService(db)
    artifacts = await service.get_scan_artifacts(scan.id)
    return success_response(
        data=[AnalysisArtifactResponse.model_validate(a).model_dump(mode="json") for a in artifacts],
        message="Analysis artifacts retrieved",
    )


@router.get("/{scan_id}/artifacts/{artifact_id}/download", summary="Download canonical analysis artifact")
async def get_artifact_download(
    scan_id: str,
    artifact_id: uuid.UUID,
    scan_context: tuple[Scan, Project, OrganizationMember] = Depends(require_scan_access),
    db: AsyncSession = Depends(get_db),
):
    """Secure direct download of canonical graph artifact JSON without exposing internal MinIO hostname."""
    scan, _, _ = scan_context
    service = ScanService(db)
    artifact, content_bytes = await service.get_artifact_content(scan.id, artifact_id)

    filename = f"{artifact.artifact_type.lower()}-{scan.id}.json"
    return Response(
        content=content_bytes,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Artifact-Type": artifact.artifact_type,
            "X-Content-Hash": artifact.content_hash,
        },
    )


@router.get("/{scan_id}/taint-evidence", summary="Get static analysis taint evidence")
async def get_taint_evidence(
    scan_id: str,
    scan_context: tuple[Scan, Project, OrganizationMember] = Depends(require_scan_access),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve structured taint evidence (attack paths, sources, sinks)."""
    scan, _, _ = scan_context
    service = ScanService(db)
    evidence = await service.get_taint_evidence(scan.id)
    return success_response(
        data=evidence,
        message="Taint evidence retrieved",
    )


@router.post("/{scan_id}/cancel", summary="Cancel a running scan")
async def cancel_scan(
    scan_id: str,
    scan_context: tuple[Scan, Project, OrganizationMember] = Depends(require_scan_access),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel an active scan."""
    scan, _, member = scan_context

    if member.role.name != "owner":
        granted = {rp.permission.key for rp in member.role.permissions if rp.permission}
        if "scan.cancel" not in granted:
            raise AuthorizationError("Permission denied: Action requires 'scan.cancel'")

    service = ScanService(db)
    await service.cancel_scan(scan.id, current_user.id)
    return success_response(message="Scan cancelled successfully")


@router.post("/{scan_id}/retry", summary="Retry a failed or timed-out scan")
async def retry_scan(
    scan_id: str,
    scan_context: tuple[Scan, Project, OrganizationMember] = Depends(require_scan_access),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retry a failed or timed-out scan."""
    scan, _, member = scan_context

    if member.role.name != "owner":
        granted = {rp.permission.key for rp in member.role.permissions if rp.permission}
        if "scan.create" not in granted:
            raise AuthorizationError("Permission denied: Action requires 'scan.create'")

    service = ScanService(db)
    retried_scan = await service.retry_scan(scan.id, current_user.id)
    return success_response(
        data=ScanResponse.model_validate(retried_scan).model_dump(mode="json"),
        message="Scan retried successfully",
    )
