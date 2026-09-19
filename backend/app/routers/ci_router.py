# ============================================================
# CI/CD REST Router (Phase 7)
# ============================================================

from __future__ import annotations

import hashlib
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.core.exceptions import AuthenticationError, NotFoundError
from backend.app.core.response import success_response
from backend.app.database.session import get_db
from backend.app.models.api_key import ApiKey
from backend.app.models.finding import Finding, FindingOccurrence
from backend.app.models.project import Project
from backend.app.models.scan import Scan
from backend.app.models.source_snapshot import SourceSnapshot
from backend.app.models.user import User
from backend.app.services.security_gate_service import SecurityGateService

router = APIRouter(prefix="/ci", tags=["CI/CD"])


async def _authenticate_api_key(
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
) -> tuple[ApiKey, User]:
    """Authenticate request using hashed API key."""
    import hashlib
    key_hash = hashlib.sha256(x_api_key.encode("utf-8")).hexdigest()

    stmt = select(ApiKey).options(selectinload(ApiKey.user)).where(ApiKey.key_hash == key_hash, ApiKey.revoked_at.is_(None))
    res = await db.execute(stmt)
    api_key = res.scalar_one_or_none()
    if not api_key or not api_key.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked API Key",
        )
    return api_key, api_key.user


@router.post("/scans", summary="Trigger CI security scan", status_code=202)
async def trigger_ci_scan(
    payload: dict[str, Any],
    auth: tuple[ApiKey, User] = Depends(_authenticate_api_key),
    db: AsyncSession = Depends(get_db),
):
    """Trigger an automated security scan from a CI/CD pipeline."""
    api_key, user = auth
    project_id_str = payload.get("project_id")
    if not project_id_str:
        raise HTTPException(status_code=400, detail="project_id is required")

    # Resolve project scoped to user's organization
    proj_stmt = select(Project).where(
        (Project.public_id == project_id_str) | (Project.id == uuid.UUID(project_id_str) if len(project_id_str) == 36 else False)
    )
    res = await db.execute(proj_stmt)
    project = res.scalar_one_or_none()
    if not project or project.organization_id != api_key.organization_id:
        raise HTTPException(status_code=404, detail="Project not found in authenticated organization")

    branch = payload.get("branch", "main")
    commit_sha = payload.get("commit_sha", "HEAD")

    # Resolve or create immutable snapshot
    snap_stmt = select(SourceSnapshot).where(
        SourceSnapshot.project_id == project.id,
        SourceSnapshot.source_version == commit_sha,
    )
    snapshot = (await db.execute(snap_stmt)).scalar_one_or_none()
    if not snapshot:
        snapshot = SourceSnapshot(
            id=uuid.uuid4(),
            project_id=project.id,
            source_type="git",
            source_version=commit_sha,
            content_hash=hashlib.sha256(commit_sha.encode("utf-8")).hexdigest(),
            artifact_uri=f"snapshots/{project.id}/{commit_sha}.zip",
            status="ready",
        )
        db.add(snapshot)
        await db.commit()
        await db.refresh(snapshot)

    # Create Scan
    scan = Scan(
        id=uuid.uuid4(),
        project_id=project.id,
        organization_id=project.organization_id,
        source_snapshot_id=snapshot.id,
        created_by=user.id,
        status="queued",
        config={"scan_type": "ci", "branch": branch, "commit_sha": commit_sha},
    )
    db.add(scan)
    await db.commit()
    await db.refresh(scan)

    logger.info(
        "CI Scan queued: {sid} for project {pid} ({branch}@{sha})",
        sid=scan.public_id,
        pid=project.public_id,
        branch=branch,
        sha=commit_sha,
    )

    return success_response(
        data={
            "scan_id": scan.public_id,
            "status": scan.status,
            "project_id": project.public_id,
            "snapshot_id": snapshot.public_id,
        },
        message="CI scan enqueued successfully",
        status_code=202,
    )


@router.get("/scans/{scan_id}", summary="Get CI scan status")
async def get_ci_scan_status(
    scan_id: str,
    auth: tuple[ApiKey, User] = Depends(_authenticate_api_key),
    db: AsyncSession = Depends(get_db),
):
    """Poll CI scan status."""
    api_key, _ = auth
    stmt = (
        select(Scan)
        .join(Project, Scan.project_id == Project.id)
        .where(
            (Scan.public_id == scan_id) | (Scan.id == uuid.UUID(scan_id) if len(scan_id) == 36 else False),
            Project.organization_id == api_key.organization_id,
        )
    )
    scan = (await db.execute(stmt)).scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    return success_response(
        data={
            "scan_id": scan.public_id,
            "status": scan.status,
            "created_at": scan.created_at.isoformat() if scan.created_at else None,
            "completed_at": scan.completed_at.isoformat() if scan.completed_at else None,
        }
    )


@router.get("/scans/{scan_id}/gate", summary="Evaluate security gate for CI scan")
async def get_ci_scan_gate(
    scan_id: str,
    auth: tuple[ApiKey, User] = Depends(_authenticate_api_key),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve security gate verdict and exit code hints for CI/CD runners."""
    api_key, _ = auth
    stmt = (
        select(Scan)
        .join(Project, Scan.project_id == Project.id)
        .where(
            (Scan.public_id == scan_id) | (Scan.id == uuid.UUID(scan_id) if len(scan_id) == 36 else False),
            Project.organization_id == api_key.organization_id,
        )
    )
    scan = (await db.execute(stmt)).scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    if scan.status == "failed":
        return success_response(
            data={
                "scan_id": scan.public_id,
                "gate_result": "SCAN_FAILED",
                "exit_code": 2,
                "summary": "Scan failed execution.",
            }
        )

    if scan.status in ("queued", "running", "analyzing"):
        return success_response(
            data={
                "scan_id": scan.public_id,
                "gate_result": "IN_PROGRESS",
                "exit_code": 0,
                "summary": f"Scan is still in progress (status: {scan.status}).",
            }
        )

    # Query findings observed in this scan
    occ_stmt = (
        select(FindingOccurrence)
        .options(selectinload(FindingOccurrence.finding))
        .where(FindingOccurrence.scan_id == scan.id)
    )
    occs = (await db.execute(occ_stmt)).scalars().all()
    scan_findings = [occ.finding for occ in occs if occ.finding]

    # Evaluate gate
    gate_service = SecurityGateService(db)
    policy = await gate_service.get_or_create_policy(scan.project_id, api_key.organization_id)
    gate_eval = gate_service.evaluate_findings(scan_findings, policy)

    exit_code = 0 if gate_eval["passed"] else 1

    return success_response(
        data={
            "scan_id": scan.public_id,
            "gate_result": gate_eval["gate_result"],
            "exit_code": exit_code,
            "summary": gate_eval["summary"],
            "failed_rules": gate_eval["failed_rules"],
            "violations_count": gate_eval["violations_count"],
            "violations": gate_eval["violations"],
            "policy_version": gate_eval["policy_version"],
        }
    )
