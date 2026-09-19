# ============================================================
# GitHub Webhook & PR Security Router (Phase 7)
# ============================================================

from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status
from loguru import logger
from sqlalchemy import desc, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.authorization import (
    get_current_user,
    require_project_access,
    resolve_active_organization,
    resolve_organization_context,
)
from backend.app.core.config import get_settings
from backend.app.core.exceptions import AuthorizationError, NotFoundError
from backend.app.core.rate_limit import RateLimiter
from backend.app.core.response import paginated_response, success_response
from backend.app.database.session import AsyncSessionLocal, get_db
from backend.app.models.organization import Organization, OrganizationMember
from backend.app.models.project import Project
from backend.app.models.repository import Repository
from backend.app.models.security_gate import (
    PRSecurityResult,
    SecurityGatePolicy,
    WebhookDelivery,
)
from backend.app.models.user import User
from backend.app.schemas.security_gate_schemas import (
    PRSecurityResultResponse,
    SecurityGatePolicyResponse,
    SecurityGatePolicyUpdate,
)
from backend.app.services.audit_service import AuditService
from backend.app.services.security_gate_service import SecurityGateService

router = APIRouter(tags=["GitHub Integrations & PR Security"])


def _verify_gate_policy_admin(member: OrganizationMember) -> None:
    if member.role.name in ("owner", "admin", "security_engineer"):
        return
    granted = {rp.permission.key for rp in member.role.permissions if rp.permission}
    if "project.settings" not in granted and "project.update" not in granted:
        raise AuthorizationError("Permission denied: Modifying security gate policy requires admin/security privileges")


# ── 1. Verified GitHub Webhook Endpoint & Integration Status ──


@router.get("/integrations/github/status", summary="Get GitHub Integration & App status")
async def get_github_integration_status(
    current_user: User = Depends(get_current_user),
):
    """Truthful status of GitHub App and webhook receiver."""
    settings = get_settings()
    app_id = getattr(settings, "github_app_id", None)
    app_configured = bool(app_id)
    return success_response(
        data={
            "app_status": "Configured" if app_configured else "Not configured",
            "webhook_status": "Active",
            "webhook_endpoint": "/api/v1/integrations/github/webhook",
            "capabilities": {
                "hmac_verified": True,
                "replay_protected": True,
                "check_runs": app_configured,
            },
        },
        message="GitHub integration status retrieved",
    )


@router.post(
    "/integrations/github/webhook",
    summary="Receive verified GitHub webhook",
    dependencies=[Depends(RateLimiter(times=60, seconds=60, scope="webhook:github"))],
)
async def handle_github_webhook(
    request: Request,
    x_github_event: str = Header(..., alias="X-GitHub-Event"),
    x_github_delivery: str = Header(..., alias="X-GitHub-Delivery"),
    x_hub_signature_256: str | None = Header(None, alias="X-Hub-Signature-256"),
    db: AsyncSession = Depends(get_db),
):
    """Securely receive, verify HMAC, and process incoming GitHub webhooks."""
    raw_body = await request.body()
    settings = get_settings()

    # 1. HMAC SHA-256 verification
    secret = getattr(settings, "github_webhook_secret", None) or "vulnscan_github_webhook_secret"
    if not x_hub_signature_256:
        logger.warning("Rejecting GitHub webhook: Missing X-Hub-Signature-256")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing HMAC signature header",
        )

    computed = "sha256=" + hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(computed, x_hub_signature_256):
        logger.warning("Rejecting GitHub webhook: Invalid signature")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook HMAC signature",
        )

    # 2. Replay protection via Delivery ID
    payload_hash = hashlib.sha256(raw_body).hexdigest()
    delivery_stmt = select(WebhookDelivery).where(WebhookDelivery.delivery_id == x_github_delivery)
    existing_del = (await db.execute(delivery_stmt)).scalar_one_or_none()
    if existing_del:
        if existing_del.payload_hash and existing_del.payload_hash != payload_hash:
            logger.warning("Rejecting conflicting webhook payload for delivery_id {did}", did=x_github_delivery)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Conflicting payload for identical delivery ID",
            )
        logger.info("Webhook delivery {did} already processed — skipping idempotently", did=x_github_delivery)
        return success_response(
            data={"delivery_id": x_github_delivery, "status": "duplicate_skipped"},
            message="Delivery previously processed",
        )

    # Record delivery
    deliv_record = WebhookDelivery(
        id=uuid.uuid4(),
        delivery_id=x_github_delivery,
        event_type=x_github_event,
        payload_hash=payload_hash,
        status="processing",
    )
    db.add(deliv_record)
    await db.commit()

    # 3. Process event
    try:
        payload = json.loads(raw_body.decode("utf-8")) if raw_body else {}
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Malformed JSON payload in webhook",
        )

    if x_github_event == "ping":
        return success_response(message="Ping received successfully")

    if x_github_event == "pull_request":
        action = payload.get("action")
        if action in ("opened", "synchronize", "reopened"):
            pr_data = payload.get("pull_request", {})
            repo_data = payload.get("repository", {})
            clone_url = repo_data.get("clone_url") or repo_data.get("html_url")

            # Map repository
            repo_stmt = (
                select(Repository)
                .options(selectinload(Repository.project))
                .where(
                    (Repository.repository_url == clone_url)
                    | (Repository.repository_url == repo_data.get("html_url"))
                )
            )
            repo = (await db.execute(repo_stmt)).scalar_one_or_none()
            if not repo:
                logger.warning("No linked project found for repository {url}", url=clone_url)
                return success_response(message="Repository not tracked in system")

            deliv_record.repository_id = repo.id
            await db.commit()

            head_sha = pr_data.get("head", {}).get("sha")
            base_sha = pr_data.get("base", {}).get("sha")
            pr_num = payload.get("number") or pr_data.get("number")
            branch_name = pr_data.get("head", {}).get("ref")
            pr_title = pr_data.get("title")

            logger.info(
                "Triggering PR scan for repo {rid}, PR #{pr}, SHA {sha}",
                rid=repo.id,
                pr=pr_num,
                sha=head_sha,
            )

            # Record initial queued PRSecurityResult
            initial_result = PRSecurityResult(
                id=uuid.uuid4(),
                organization_id=repo.project.organization_id if repo.project else uuid.uuid4(),
                project_id=repo.project_id,
                repository_id=repo.id,
                pull_request_number=pr_num,
                pr_title=pr_title,
                pr_head_sha=head_sha,
                pr_base_sha=base_sha,
                pr_branch=branch_name,
                status="QUEUED",
                gate_result="QUEUED",
            )
            db.add(initial_result)
            await db.commit()

            return success_response(
                data={"pr_security_result_id": initial_result.public_id},
                message=f"PR #{pr_num} webhook accepted and queued for scan",
                status_code=202,
            )

    return success_response(message=f"Event '{x_github_event}' ignored")


# ── 2. Security Gate Policy Management ─────────────────────────


@router.get(
    "/projects/{project_id}/gate-policy",
    summary="Get project security gate policy",
)
@router.get(
    "/projects/{project_id}/security-gate",
    summary="Get project security gate policy (alias)",
    include_in_schema=False,
)
async def get_security_gate_policy(
    project_id: str,
    project_context: tuple[Project, OrganizationMember] = Depends(require_project_access),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve security gate policy for a project."""
    project, _ = project_context
    service = SecurityGateService(db)
    policy = await service.get_or_create_policy(project.id, project.organization_id)
    return success_response(
        data=SecurityGatePolicyResponse.model_validate(policy).model_dump(mode="json"),
        message="Security gate policy retrieved",
    )


@router.put(
    "/projects/{project_id}/gate-policy",
    summary="Update project security gate policy",
)
@router.put(
    "/projects/{project_id}/security-gate",
    summary="Update project security gate policy (alias)",
    include_in_schema=False,
)
async def update_security_gate_policy(
    project_id: str,
    body: SecurityGatePolicyUpdate,
    project_context: tuple[Project, OrganizationMember] = Depends(require_project_access),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Configure security gate rules (Critical/High/Secret/CVSS toggles)."""
    project, member = project_context
    _verify_gate_policy_admin(member)

    service = SecurityGateService(db)
    policy = await service.get_or_create_policy(project.id, project.organization_id)

    if body.name is not None:
        policy.name = body.name
    if body.block_new_critical is not None:
        policy.block_new_critical = body.block_new_critical
    if body.block_new_high is not None:
        policy.block_new_high = body.block_new_high
    if body.block_secrets is not None:
        policy.block_secrets = body.block_secrets
    if body.cvss_threshold is not None:
        policy.cvss_threshold = body.cvss_threshold

    await db.commit()
    await db.refresh(policy)

    audit = AuditService(db)
    await audit.log(
        user_id=current_user.id,
        action="security_gate_policy.updated",
        resource_type="security_gate_policy",
        resource_id=str(policy.id),
        metadata={
            "block_critical": policy.block_new_critical,
            "block_high": policy.block_new_high,
            "block_secrets": policy.block_secrets,
            "cvss_threshold": policy.cvss_threshold,
        },
    )

    return success_response(
        data=SecurityGatePolicyResponse.model_validate(policy).model_dump(mode="json"),
        message="Security gate policy updated successfully",
    )


# ── 3. PR Security Results Listing & Details ───────────────────


@router.get(
    "/projects/{project_id}/pr-results",
    summary="List PR security results for project",
)
async def list_pr_security_results(
    project_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    project_context: tuple[Project, OrganizationMember] = Depends(require_project_access),
    db: AsyncSession = Depends(get_db),
):
    """List historical PR security scan results and gate verdicts."""
    project, _ = project_context
    stmt = (
        select(PRSecurityResult)
        .where(PRSecurityResult.project_id == project.id)
        .order_by(PRSecurityResult.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    res = await db.execute(stmt)
    items = res.scalars().all()

    count_stmt = select(PRSecurityResult).where(PRSecurityResult.project_id == project.id)
    total = len((await db.execute(count_stmt)).scalars().all())

    return paginated_response(
        items=[PRSecurityResultResponse.model_validate(item).model_dump(mode="json") for item in items],
        total=total,
        page=page,
        page_size=page_size,
        message="PR security results retrieved",
    )


@router.get(
    "/projects/{project_id}/pr-results/{result_id}",
    summary="Get single PR security result detail",
)
async def get_pr_security_result_detail(
    project_id: str,
    result_id: str,
    project_context: tuple[Project, OrganizationMember] = Depends(require_project_access),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve detailed finding comparison (Existing, New, Fixed) and gate verdict for a PR."""
    project, _ = project_context
    stmt = select(PRSecurityResult).where(
        PRSecurityResult.project_id == project.id,
        (PRSecurityResult.public_id == result_id) | (PRSecurityResult.id == uuid.UUID(result_id) if len(result_id) == 36 else False),
    )
    res = await db.execute(stmt)
    result = res.scalar_one_or_none()
    if not result:
        raise NotFoundError("PR security result not found")

    return success_response(
        data=PRSecurityResultResponse.model_validate(result).model_dump(mode="json"),
        message="PR security result retrieved",
    )
