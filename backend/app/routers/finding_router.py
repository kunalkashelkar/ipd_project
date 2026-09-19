# ============================================================
# Finding Router — Vulnerability Findings & Investigation APIs (Phase 5)
# ============================================================
# Tenant-safe REST endpoints for finding management, lifecycle transitions,
# evidence inspection, and immutable snapshot source presentation.
# ============================================================

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.core.authorization import (
    get_current_user,
    require_finding_access,
    require_permission,
    require_project_access,
    require_scan_access,
)
from backend.app.core.exceptions import AuthorizationError, NotFoundError, ValidationError
from backend.app.core.response import paginated_response, success_response
from backend.app.database.session import get_db
from backend.app.models.finding import (
    Finding,
    FindingAssignment,
    FindingComment,
    FindingOccurrence,
    FindingStatusHistory,
    FindingSuppression,
)
from backend.app.models.organization import Organization, OrganizationMember
from backend.app.models.project import Project
from backend.app.models.scan import Scan
from backend.app.models.source_snapshot import SourceFile
from backend.app.models.user import User
from backend.app.schemas.finding_schemas import (
    FindingAssignRequest,
    FindingAssignmentResponse,
    FindingCommentCreate,
    FindingCommentResponse,
    FindingDetailResponse,
    FindingListItem,
    FindingOccurrenceResponse,
    FindingSourceContextResponse,
    FindingStatusHistoryResponse,
    FindingStatusTransitionRequest,
    FindingSuppressionRequest,
    FindingSuppressionResponse,
    GlobalFindingsSummary,
    ProjectFindingsSummary,
)
from backend.app.services.audit_service import AuditService
from backend.app.services.finding_service.lifecycle import FindingLifecycleService
from backend.app.storage.service import StorageService

router = APIRouter(tags=["Findings"])


# ── Helper for permission checks on Member ────────────────────
def _verify_member_permission(member: OrganizationMember, required_key: str) -> None:
    if member.role.name == "owner":
        return
    granted = {rp.permission.key for rp in member.role.permissions if rp.permission}
    if required_key not in granted:
        raise AuthorizationError(f"Permission denied: Action requires '{required_key}'")


# ── 0. Global Findings Listing & Summary (Active Organization) ──────


@router.get("/findings", summary="List global findings for active organization")
async def list_global_findings(
    severity: str | None = Query(None),
    status: str | None = Query(None),
    cwe: str | None = Query(None),
    project_id: str | None = Query(None),
    search: str | None = Query(None),
    sort_by: str = Query("risk_score", pattern="^(risk_score|severity|last_seen_at|first_seen_at|created_at)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    org_context: tuple[Organization, OrganizationMember] = Depends(require_permission("finding.read")),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve paginated and filtered vulnerability findings across the active organization."""
    org, _ = org_context

    query = (
        select(Finding)
        .join(Project, Finding.project_id == Project.id)
        .where(Finding.organization_id == org.id)
    )

    # Active finding semantics: exclude FALSE_POSITIVE and SUPPRESSED unless explicitly filtered
    if status:
        query = query.where(func.upper(Finding.status) == status.upper().strip())
    else:
        query = query.where(func.upper(Finding.status).notin_(["FALSE_POSITIVE", "SUPPRESSED"]))

    if severity:
        query = query.where(func.lower(Finding.severity) == severity.lower().strip())
    if cwe:
        query = query.where(Finding.cwe_id.ilike(f"%{cwe.strip()}%"))

    if project_id:
        from backend.app.core.identifiers import is_valid_uuid
        from sqlalchemy import or_
        pid_str = str(project_id).strip()
        if is_valid_uuid(pid_str):
            cond = or_(Project.id == uuid.UUID(pid_str), Project.public_id == pid_str)
        else:
            cond = (Project.public_id == pid_str)
        proj_stmt = select(Project.id).where(cond, Project.organization_id == org.id)
        proj_res = await db.execute(proj_stmt)
        resolved_pid = proj_res.scalar_one_or_none()
        if resolved_pid is None:
            raise NotFoundError("Project not found")
        query = query.where(Finding.project_id == resolved_pid)

    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.where(
            (Finding.title.ilike(search_pattern))
            | (Finding.vulnerability_type.ilike(search_pattern))
            | (Finding.cwe_id.ilike(search_pattern))
            | (Project.name.ilike(search_pattern))
        )

    # Count total
    count_stmt = select(func.count()).select_from(query.subquery())
    total_res = await db.execute(count_stmt)
    total = total_res.scalar() or 0

    # Sorting
    sort_col = getattr(Finding, sort_by, Finding.risk_score)
    if sort_order == "desc":
        query = query.order_by(desc(sort_col))
    else:
        query = query.order_by(sort_col)

    # Pagination & eager load project + occurrences with scan
    query = (
        query.offset((page - 1) * page_size)
        .limit(page_size)
        .options(
            selectinload(Finding.project),
            selectinload(Finding.occurrences).selectinload(FindingOccurrence.scan),
            selectinload(Finding.occurrences).selectinload(FindingOccurrence.ai_prediction),
        )
    )

    res = await db.execute(query)
    findings = res.scalars().all()

    items: list[FindingListItem] = []
    for f in findings:
        latest_occ = f.occurrences[0] if f.occurrences else None
        latest_scan = latest_occ.scan if latest_occ else None
        items.append(
            FindingListItem(
                id=f.id,
                public_id=f.public_id,
                project_id=f.project_id,
                project_name=f.project.name if f.project else None,
                project_public_id=f.project.public_id if f.project else None,
                organization_id=f.organization_id,
                title=f.title,
                vulnerability_type=f.vulnerability_type,
                cwe_id=f.cwe_id,
                severity=f.severity,
                cvss_score=f.cvss_score,
                confidence=f.confidence,
                risk_score=f.risk_score,
                status=f.status,
                fingerprint=f.fingerprint,
                first_seen_at=f.first_seen_at,
                last_seen_at=f.last_seen_at,
                fixed_at=f.fixed_at,
                latest_file_path=latest_occ.file_path if latest_occ else None,
                latest_line_number=latest_occ.start_line if latest_occ else None,
                latest_scan_id=latest_scan.id if latest_scan else None,
                latest_scan_public_id=latest_scan.public_id if latest_scan else None,
                occurrence_count=len(f.occurrences),
            )
        )

    return paginated_response(
        items=[item.model_dump(mode="json") for item in items],
        total=total,
        page=page,
        page_size=page_size,
        message="Global findings retrieved successfully",
    )


@router.get("/findings/summary", summary="Get global findings summary")
async def get_global_findings_summary(
    org_context: tuple[Organization, OrganizationMember] = Depends(require_permission("finding.read")),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve aggregate summary counts for active findings across the active organization."""
    org, _ = org_context

    # Query active findings excluding FALSE_POSITIVE and SUPPRESSED
    base_query = (
        select(func.lower(Finding.severity), func.count(func.distinct(Finding.id)))
        .where(
            Finding.organization_id == org.id,
            func.upper(Finding.status).notin_(["FALSE_POSITIVE", "SUPPRESSED"]),
        )
        .group_by(func.lower(Finding.severity))
    )
    res = await db.execute(base_query)
    sev_map = dict(res.all())

    total = sum(sev_map.values())
    summary = GlobalFindingsSummary(
        total=total,
        critical=sev_map.get("critical", 0),
        high=sev_map.get("high", 0),
        medium=sev_map.get("medium", 0),
        low=sev_map.get("low", 0),
        info=sev_map.get("info", 0),
    )
    return success_response(
        data=summary.model_dump(mode="json"),
        message="Global findings summary retrieved successfully",
    )


# ── 1. Project Findings Listing & Summary ─────────────────────


@router.get("/projects/{project_id}/findings", summary="List project findings")
async def list_project_findings(
    project_id: str,
    severity: str | None = Query(None),
    status: str | None = Query(None),
    cwe: str | None = Query(None),
    search: str | None = Query(None),
    sort_by: str = Query("risk_score", pattern="^(risk_score|severity|last_seen_at|first_seen_at|created_at)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    project_context: tuple[Project, OrganizationMember] = Depends(require_project_access),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve paginated and filtered vulnerability findings for a project."""
    project, member = project_context
    _verify_member_permission(member, "finding.read")

    query = select(Finding).where(Finding.project_id == project.id)

    if severity:
        query = query.where(func.lower(Finding.severity) == severity.lower().strip())
    if status:
        query = query.where(func.upper(Finding.status) == status.upper().strip())
    if cwe:
        query = query.where(Finding.cwe_id.ilike(f"%{cwe.strip()}%"))
    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.where(
            (Finding.title.ilike(search_pattern))
            | (Finding.vulnerability_type.ilike(search_pattern))
            | (Finding.cwe_id.ilike(search_pattern))
        )

    # Count total
    count_stmt = select(func.count()).select_from(query.subquery())
    total_res = await db.execute(count_stmt)
    total = total_res.scalar() or 0

    # Sorting
    sort_col = getattr(Finding, sort_by, Finding.risk_score)
    if sort_order == "desc":
        query = query.order_by(desc(sort_col))
    else:
        query = query.order_by(sort_col)

    # Pagination & eager load occurrences with scan
    query = (
        query.offset((page - 1) * page_size)
        .limit(page_size)
        .options(
            selectinload(Finding.project),
            selectinload(Finding.occurrences).selectinload(FindingOccurrence.scan),
            selectinload(Finding.occurrences).selectinload(FindingOccurrence.ai_prediction),
        )
    )

    res = await db.execute(query)
    findings = res.scalars().all()

    items: list[FindingListItem] = []
    for f in findings:
        latest_occ = f.occurrences[0] if f.occurrences else None
        latest_scan = latest_occ.scan if latest_occ else None
        items.append(
            FindingListItem(
                id=f.id,
                public_id=f.public_id,
                project_id=f.project_id,
                project_name=project.name,
                project_public_id=project.public_id,
                organization_id=f.organization_id,
                title=f.title,
                vulnerability_type=f.vulnerability_type,
                cwe_id=f.cwe_id,
                severity=f.severity,
                cvss_score=f.cvss_score,
                confidence=f.confidence,
                risk_score=f.risk_score,
                status=f.status,
                fingerprint=f.fingerprint,
                first_seen_at=f.first_seen_at,
                last_seen_at=f.last_seen_at,
                fixed_at=f.fixed_at,
                latest_file_path=latest_occ.file_path if latest_occ else None,
                latest_line_number=latest_occ.start_line if latest_occ else None,
                latest_scan_id=latest_scan.id if latest_scan else None,
                latest_scan_public_id=latest_scan.public_id if latest_scan else None,
                occurrence_count=len(f.occurrences),
            )
        )

    return paginated_response(
        items=[item.model_dump(mode="json") for item in items],
        total=total,
        page=page,
        page_size=page_size,
        message="Findings retrieved successfully",
    )


@router.get("/projects/{project_id}/findings/summary", summary="Get project findings summary")
async def get_project_findings_summary(
    project_id: str,
    project_context: tuple[Project, OrganizationMember] = Depends(require_project_access),
    db: AsyncSession = Depends(get_db),
):
    """Get aggregated severity and lifecycle status statistics for project findings."""
    project, member = project_context
    _verify_member_permission(member, "finding.read")

    stmt = select(Finding.severity, Finding.status).where(Finding.project_id == project.id)
    res = await db.execute(stmt)
    rows = res.all()

    summary = ProjectFindingsSummary(total=len(rows))
    for sev, stat in rows:
        sev_k = sev.lower().strip() if sev else ""
        if sev_k == "critical":
            summary.critical += 1
        elif sev_k == "high":
            summary.high += 1
        elif sev_k == "medium":
            summary.medium += 1
        elif sev_k == "low":
            summary.low += 1

        stat_k = stat.upper().strip() if stat else ""
        if stat_k == "OPEN":
            summary.open += 1
        elif stat_k == "CONFIRMED":
            summary.confirmed += 1
        elif stat_k == "IN_PROGRESS":
            summary.in_progress += 1
        elif stat_k in ("FIXED", "VERIFIED"):
            summary.fixed += 1
        elif stat_k == "SUPPRESSED":
            summary.suppressed += 1
        elif stat_k == "FALSE_POSITIVE":
            summary.false_positive += 1
        elif stat_k == "RISK_ACCEPTED":
            summary.risk_accepted += 1

    return success_response(
        data=summary.model_dump(mode="json"),
        message="Project findings summary retrieved successfully",
    )


# ── 2. Scan Specific Findings ─────────────────────────────────


@router.get("/scans/{scan_id}/findings", summary="Get findings observed in a scan")
async def get_scan_findings(
    scan_id: str,
    scan_context: tuple[Scan, Project, OrganizationMember] = Depends(require_scan_access),
    db: AsyncSession = Depends(get_db),
):
    """List all findings observed in a particular scan via their occurrences."""
    scan, project, member = scan_context
    _verify_member_permission(member, "finding.read")

    stmt = (
        select(Finding)
        .join(FindingOccurrence, FindingOccurrence.finding_id == Finding.id)
        .where(FindingOccurrence.scan_id == scan.id)
        .options(
            selectinload(Finding.project),
            selectinload(Finding.occurrences).selectinload(FindingOccurrence.scan),
            selectinload(Finding.occurrences).selectinload(FindingOccurrence.ai_prediction),
        )
        .distinct()
    )
    res = await db.execute(stmt)
    findings = res.scalars().all()

    items = [
        FindingListItem(
            id=f.id,
            public_id=f.public_id,
            project_id=f.project_id,
            project_name=project.name,
            project_public_id=project.public_id,
            organization_id=f.organization_id,
            title=f.title,
            vulnerability_type=f.vulnerability_type,
            cwe_id=f.cwe_id,
            severity=f.severity,
            cvss_score=f.cvss_score,
            confidence=f.confidence,
            risk_score=f.risk_score,
            status=f.status,
            fingerprint=f.fingerprint,
            first_seen_at=f.first_seen_at,
            last_seen_at=f.last_seen_at,
            fixed_at=f.fixed_at,
            latest_file_path=f.occurrences[0].file_path if f.occurrences else None,
            latest_line_number=f.occurrences[0].start_line if f.occurrences else None,
            latest_scan_id=scan.id,
            latest_scan_public_id=scan.public_id,
            occurrence_count=len(f.occurrences),
        ).model_dump(mode="json")
        for f in findings
    ]

    return success_response(data=items, message="Scan findings retrieved successfully")


# ── 3. Finding Detail & Investigation ─────────────────────────


@router.get("/findings/{finding_id}", summary="Get finding detail")
async def get_finding_detail(
    finding_id: str,
    finding_context: tuple[Finding, Project, OrganizationMember] = Depends(require_finding_access),
    db: AsyncSession = Depends(get_db),
):
    """Get complete finding detail including occurrences, AI predictions, and history."""
    finding, _, _ = finding_context

    # Eager load related domain entities
    stmt = (
        select(Finding)
        .where(Finding.id == finding.id)
        .options(
            selectinload(Finding.occurrences).selectinload(FindingOccurrence.ai_prediction),
            selectinload(Finding.status_history),
            selectinload(Finding.assignments),
            selectinload(Finding.comments),
            selectinload(Finding.suppressions),
        )
    )
    res = await db.execute(stmt)
    loaded_finding = res.scalar_one()

    occurrences_data = [
        FindingOccurrenceResponse.model_validate(occ) for occ in loaded_finding.occurrences
    ]
    latest_occ = occurrences_data[0] if occurrences_data else None

    finding, project, _ = finding_context

    detail = FindingDetailResponse(
        id=loaded_finding.id,
        public_id=loaded_finding.public_id,
        project_id=loaded_finding.project_id,
        project_public_id=project.public_id,
        project_name=project.name,
        organization_id=loaded_finding.organization_id,
        title=loaded_finding.title,
        vulnerability_type=loaded_finding.vulnerability_type,
        cwe_id=loaded_finding.cwe_id,
        severity=loaded_finding.severity,
        cvss_score=loaded_finding.cvss_score,
        confidence=loaded_finding.confidence,
        risk_score=loaded_finding.risk_score,
        risk_version=loaded_finding.risk_version,
        status=loaded_finding.status,
        fingerprint=loaded_finding.fingerprint,
        fingerprint_version=loaded_finding.fingerprint_version,
        first_seen_at=loaded_finding.first_seen_at,
        last_seen_at=loaded_finding.last_seen_at,
        fixed_at=loaded_finding.fixed_at,
        created_at=loaded_finding.created_at,
        updated_at=loaded_finding.updated_at,
        latest_occurrence=latest_occ,
        occurrences=occurrences_data,
        status_history=[FindingStatusHistoryResponse.model_validate(sh) for sh in loaded_finding.status_history],
        assignments=[FindingAssignmentResponse.model_validate(asg) for asg in loaded_finding.assignments],
        comments=[FindingCommentResponse.model_validate(c) for c in loaded_finding.comments],
        suppressions=[FindingSuppressionResponse.model_validate(sp) for sp in loaded_finding.suppressions],
    )

    return success_response(
        data=detail.model_dump(mode="json"),
        message="Finding details retrieved successfully",
    )


@router.get("/findings/{finding_id}/source", summary="Get finding source code context")
async def get_finding_source_context(
    finding_id: uuid.UUID,
    window: int = Query(15, ge=5, le=50),
    finding_context: tuple[Finding, Project, OrganizationMember] = Depends(require_finding_access),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve verified source code context from the exact immutable snapshot."""
    finding, _, _ = finding_context

    # Get latest occurrence
    occ_stmt = (
        select(FindingOccurrence)
        .where(FindingOccurrence.finding_id == finding_id)
        .order_by(desc(FindingOccurrence.observed_at))
        .limit(1)
    )
    occ_res = await db.execute(occ_stmt)
    latest_occ = occ_res.scalar_one_or_none()

    if not latest_occ:
        raise NotFoundError("No occurrence recorded for this finding")

    # Find SourceFile record in the snapshot
    sf_stmt = select(SourceFile).where(
        SourceFile.source_snapshot_id == latest_occ.source_snapshot_id,
        SourceFile.relative_path == latest_occ.file_path,
    )
    sf_res = await db.execute(sf_stmt)
    source_file = sf_res.scalar_one_or_none()

    if not source_file:
        raise NotFoundError(f"Source file '{latest_occ.file_path}' not found in snapshot")

    # Retrieve source code bytes from MinIO
    storage = StorageService()
    try:
        source_bytes = await storage.read_file(source_file.original_artifact_uri)
        content_str = source_bytes.decode(source_file.encoding or "utf-8", errors="replace")
    except Exception as exc:
        raise NotFoundError(f"Failed to load immutable source artifact: {exc}")

    lines = content_str.splitlines()
    target_line = latest_occ.start_line or 1
    start_l = max(1, target_line - window)
    end_l = min(len(lines), target_line + window)

    # Slice the lines (1-indexed)
    snippet_lines = lines[start_l - 1 : end_l]
    snippet_str = "\n".join(snippet_lines)

    resp = FindingSourceContextResponse(
        file_path=latest_occ.file_path,
        language=source_file.language,
        line_number=latest_occ.start_line,
        start_line=start_l,
        end_line=end_l,
        source_snippet=snippet_str,
        snapshot_id=latest_occ.source_snapshot_id,
        is_snapshot_immutable=True,
    )

    return success_response(data=resp.model_dump(mode="json"), message="Source context retrieved")


# ── 4. Lifecycle Mutations ────────────────────────────────────


@router.post("/findings/{finding_id}/status", summary="Transition finding status")
async def transition_finding_status(
    finding_id: uuid.UUID,
    body: FindingStatusTransitionRequest,
    finding_context: tuple[Finding, Project, OrganizationMember] = Depends(require_finding_access),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Enforce controlled lifecycle transition with audit logging."""
    finding, _, member = finding_context
    _verify_member_permission(member, "finding.update")

    lifecycle_svc = FindingLifecycleService(db)
    history = await lifecycle_svc.transition_status(
        finding=finding,
        new_status=body.status,
        actor_id=current_user.id,
        reason=body.reason,
    )
    await db.commit()

    return success_response(
        data=FindingStatusHistoryResponse.model_validate(history).model_dump(mode="json"),
        message=f"Finding status transitioned to '{body.status}'",
    )


@router.post("/findings/{finding_id}/assign", summary="Assign finding to member")
async def assign_finding(
    finding_id: uuid.UUID,
    body: FindingAssignRequest,
    finding_context: tuple[Finding, Project, OrganizationMember] = Depends(require_finding_access),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Assign finding to an active organization member."""
    finding, project, member = finding_context
    _verify_member_permission(member, "finding.assign")

    # Verify target user is an active member of the same organization
    target_member_stmt = select(OrganizationMember).where(
        OrganizationMember.organization_id == project.organization_id,
        OrganizationMember.user_id == body.user_id,
        OrganizationMember.status == "active",
    )
    res = await db.execute(target_member_stmt)
    if not res.scalar_one_or_none():
        raise ValidationError("Target user is not an active member of this organization")

    # Deactivate previous active assignments
    curr_asg_stmt = select(FindingAssignment).where(
        FindingAssignment.finding_id == finding_id, FindingAssignment.active.is_(True)
    )
    curr_res = await db.execute(curr_asg_stmt)
    for ca in curr_res.scalars().all():
        ca.active = False

    new_assignment = FindingAssignment(
        id=uuid.uuid4(),
        finding_id=finding_id,
        assigned_to_user_id=body.user_id,
        assigned_by_user_id=current_user.id,
        active=True,
    )
    db.add(new_assignment)

    audit = AuditService(db)
    await audit.log(
        user_id=current_user.id,
        action="finding_assigned",
        resource_type="finding",
        resource_id=str(finding_id),
        metadata={"assigned_to": str(body.user_id)},
    )

    # Notify assigned user if assigned by someone else
    if body.user_id != current_user.id:
        from backend.app.services.notification_service import NotificationService
        notif_svc = NotificationService(db)
        await notif_svc.create_notification(
            user_id=body.user_id,
            organization_id=project.organization_id,
            type="finding_assigned",
            title="Finding Assigned to You",
            body=f"{current_user.name or current_user.email} assigned finding {finding.public_id} ({finding.title}) to you.",
            severity="info",
            entity_type="finding",
            entity_id=finding.id,
            link_url=f"/findings/{finding.public_id}",
            event_key=f"assign:{finding.id}:{body.user_id}:{new_assignment.id}",
        )

    await db.commit()

    return success_response(
        data=FindingAssignmentResponse.model_validate(new_assignment).model_dump(mode="json"),
        message="Finding assigned successfully",
    )


@router.post("/findings/{finding_id}/comments", summary="Add comment to finding", status_code=201)
async def add_finding_comment(
    finding_id: uuid.UUID,
    body: FindingCommentCreate,
    finding_context: tuple[Finding, Project, OrganizationMember] = Depends(require_finding_access),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a collaboration comment to a finding with @mention detection."""
    finding, project, member = finding_context
    _verify_member_permission(member, "finding.read")

    comment = FindingComment(
        id=uuid.uuid4(),
        finding_id=finding_id,
        author_id=current_user.id,
        content=body.content.strip(),
    )
    db.add(comment)

    audit = AuditService(db)
    await audit.log(
        user_id=current_user.id,
        action="finding_comment_added",
        resource_type="finding",
        resource_id=str(finding_id),
    )

    # Detect @username mentions and notify organization members
    import re
    from backend.app.services.notification_service import NotificationService
    mentions = set(re.findall(r"@([a-zA-Z0-9_\-\.]+)", body.content))
    if mentions:
        notif_svc = NotificationService(db)
        for handle in mentions:
            u_stmt = (
                select(User)
                .join(OrganizationMember, OrganizationMember.user_id == User.id)
                .where(
                    OrganizationMember.organization_id == project.organization_id,
                    OrganizationMember.status == "active",
                    (User.email.ilike(f"{handle}%")) | (User.name.ilike(f"%{handle}%")),
                )
            )
            u_res = await db.execute(u_stmt)
            mentioned_user = u_res.scalar_one_or_none()
            if mentioned_user and mentioned_user.id != current_user.id:
                await notif_svc.notify_user_mentioned(
                    comment_id=comment.id,
                    finding_id=finding.id,
                    finding_public_id=finding.public_id,
                    mentioned_user_id=mentioned_user.id,
                    author_name=current_user.name or current_user.email,
                    organization_id=project.organization_id,
                )

    await db.commit()

    return success_response(
        data=FindingCommentResponse.model_validate(comment).model_dump(mode="json"),
        message="Comment added successfully",
        status_code=201,
    )


@router.get("/findings/{finding_id}/activity", summary="Get finding activity stream")
async def get_finding_activity(
    finding_id: uuid.UUID,
    finding_context: tuple[Finding, Project, OrganizationMember] = Depends(require_finding_access),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve full chronological activity stream for a finding."""
    finding, project, member = finding_context
    _verify_member_permission(member, "finding.read")

    activities = []

    # 1. Status history
    hist_stmt = (
        select(FindingStatusHistory)
        .options(selectinload(FindingStatusHistory.actor))
        .where(FindingStatusHistory.finding_id == finding_id)
    )
    hist_res = await db.execute(hist_stmt)
    for h in hist_res.scalars().all():
        actor_name = h.actor.name or h.actor.email if h.actor else "System"
        activities.append({
            "id": f"status_{h.id}",
            "activity_type": "status_change",
            "title": f"Status changed to {h.new_status}",
            "description": h.reason or f"Transitioned from {h.previous_status or 'INITIAL'}",
            "actor_name": actor_name,
            "created_at": h.created_at.isoformat() if h.created_at else None,
            "metadata": {"new_status": h.new_status, "previous_status": h.previous_status},
        })

    # 2. Assignments
    asg_stmt = (
        select(FindingAssignment)
        .options(selectinload(FindingAssignment.assigned_to), selectinload(FindingAssignment.assigned_by))
        .where(FindingAssignment.finding_id == finding_id)
    )
    asg_res = await db.execute(asg_stmt)
    for a in asg_res.scalars().all():
        to_name = a.assigned_to.name or a.assigned_to.email if a.assigned_to else "User"
        by_name = a.assigned_by.name or a.assigned_by.email if a.assigned_by else "System"
        activities.append({
            "id": f"asg_{a.id}",
            "activity_type": "assignment",
            "title": f"Assigned to {to_name}",
            "description": f"Assigned by {by_name}",
            "actor_name": by_name,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "metadata": {"assigned_to": to_name, "active": a.active},
        })

    # 3. Comments
    com_stmt = (
        select(FindingComment)
        .options(selectinload(FindingComment.author))
        .where(FindingComment.finding_id == finding_id)
    )
    com_res = await db.execute(com_stmt)
    for c in com_res.scalars().all():
        author_name = c.author.name or c.author.email if c.author else "User"
        activities.append({
            "id": f"com_{c.id}",
            "activity_type": "comment",
            "title": f"Comment from {author_name}",
            "description": c.content,
            "actor_name": author_name,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "metadata": {"author_id": str(c.author_id)},
        })

    # Sort chronological descending
    activities.sort(key=lambda x: x["created_at"] or "", reverse=True)

    return success_response(
        data=activities,
        message="Finding activity retrieved successfully",
    )


@router.get("/findings/{finding_id}/comments", summary="Get finding comments")
async def get_finding_comments(
    finding_id: uuid.UUID,
    finding_context: tuple[Finding, Project, OrganizationMember] = Depends(require_finding_access),
    db: AsyncSession = Depends(get_db),
):
    """Get all comments for a finding."""
    _, _, member = finding_context
    _verify_member_permission(member, "finding.read")

    stmt = (
        select(FindingComment)
        .where(FindingComment.finding_id == finding_id)
        .order_by(FindingComment.created_at.asc())
    )
    res = await db.execute(stmt)
    comments = res.scalars().all()

    return success_response(
        data=[FindingCommentResponse.model_validate(c).model_dump(mode="json") for c in comments],
        message="Comments retrieved successfully",
    )


@router.post("/findings/{finding_id}/suppress", summary="Suppress or accept risk for finding")
async def suppress_finding(
    finding_id: uuid.UUID,
    body: FindingSuppressionRequest,
    finding_context: tuple[Finding, Project, OrganizationMember] = Depends(require_finding_access),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Controlled suppression, false positive marking, or risk acceptance."""
    finding, _, member = finding_context

    if body.suppression_type == "RISK_ACCEPTED":
        _verify_member_permission(member, "finding.accept_risk")
    else:
        _verify_member_permission(member, "finding.suppress")

    lifecycle_svc = FindingLifecycleService(db)
    await lifecycle_svc.transition_status(
        finding=finding,
        new_status=body.suppression_type,
        actor_id=current_user.id,
        reason=body.reason,
    )

    suppression = FindingSuppression(
        id=uuid.uuid4(),
        finding_id=finding_id,
        actor_id=current_user.id,
        suppression_type=body.suppression_type,
        reason=body.reason,
        expires_at=body.expires_at,
        active=True,
    )
    db.add(suppression)
    await db.commit()

    return success_response(
        data=FindingSuppressionResponse.model_validate(suppression).model_dump(mode="json"),
        message=f"Finding marked as '{body.suppression_type}'",
    )


@router.post("/findings/{finding_id}/unsuppress", summary="Unsuppress finding")
async def unsuppress_finding(
    finding_id: uuid.UUID,
    finding_context: tuple[Finding, Project, OrganizationMember] = Depends(require_finding_access),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reopen a suppressed finding."""
    finding, _, member = finding_context
    _verify_member_permission(member, "finding.suppress")

    if finding.status not in ("SUPPRESSED", "FALSE_POSITIVE", "RISK_ACCEPTED"):
        raise ValidationError(f"Finding is not in a suppressed state (current: '{finding.status}')")

    lifecycle_svc = FindingLifecycleService(db)
    await lifecycle_svc.transition_status(
        finding=finding,
        new_status="OPEN",
        actor_id=current_user.id,
        reason="Suppression removed by user",
    )

    # Deactivate active suppressions
    sp_stmt = select(FindingSuppression).where(
        FindingSuppression.finding_id == finding_id, FindingSuppression.active.is_(True)
    )
    sp_res = await db.execute(sp_stmt)
    for sp in sp_res.scalars().all():
        sp.active = False

    await db.commit()
    return success_response(message="Finding reopened successfully")
