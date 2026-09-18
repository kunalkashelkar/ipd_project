# ============================================================
# Remediation Router — LLM Fixes & Multi-Stage Validation (Phase 6)
# ============================================================
# Tenant-safe REST endpoints for proposed vulnerability remediations,
# unified diff patch review, sandboxed validation, and authoritative verification.
# ============================================================

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.core.authorization import (
    get_current_user,
    require_finding_access,
    require_remediation_access,
    require_validation_access,
)
from backend.app.core.exceptions import AuthorizationError, NotFoundError
from backend.app.core.response import success_response
from backend.app.database.session import get_db
from backend.app.models.finding import Finding
from backend.app.models.organization import OrganizationMember
from backend.app.models.project import Project
from backend.app.models.remediation import Remediation, RemediationValidation
from backend.app.models.user import User
from backend.app.schemas.remediation_schemas import (
    GenerateRemediationRequest,
    RemediationResponse,
    RemediationReviewRequest,
    RemediationValidationResponse,
    ValidateRemediationRequest,
    VerificationStatusResponse,
)
from backend.app.services.remediation.service import RemediationService

router = APIRouter(tags=["Remediation & Validation"])


def _verify_member_permission(member: OrganizationMember, required_key: str) -> None:
    if member.role.name == "owner":
        return
    granted = {rp.permission.key for rp in member.role.permissions if rp.permission}
    if required_key not in granted:
        raise AuthorizationError(f"Permission denied: Action requires '{required_key}'")


# ── 1. Finding-Scoped Remediation Endpoints ───────────────────


@router.get("/findings/{finding_id}/remediations", summary="List remediations for finding")
async def list_finding_remediations(
    finding_id: uuid.UUID,
    finding_context: tuple[Finding, Project, OrganizationMember] = Depends(require_finding_access),
    db: AsyncSession = Depends(get_db),
):
    """List all proposed remediation attempts for a security finding."""
    finding, project, member = finding_context
    _verify_member_permission(member, "remediation.read")

    query = (
        select(Remediation)
        .where(
            Remediation.finding_id == finding_id,
            Remediation.organization_id == project.organization_id,
        )
        .options(selectinload(Remediation.validations))
        .order_by(desc(Remediation.remediation_number))
    )
    result = await db.execute(query)
    remediations = result.scalars().all()

    items = [RemediationResponse.model_validate(r).model_dump(mode="json") for r in remediations]
    return success_response(data=items, message=f"Retrieved {len(items)} remediation(s)")


@router.post("/findings/{finding_id}/remediations", summary="Generate remediation for finding")
async def generate_finding_remediation(
    finding_id: uuid.UUID,
    body: GenerateRemediationRequest = GenerateRemediationRequest(),
    finding_context: tuple[Finding, Project, OrganizationMember] = Depends(require_finding_access),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a new proposed remediation with unified diff patch."""
    finding, project, member = finding_context
    _verify_member_permission(member, "remediation.generate")

    rem_service = RemediationService(db)
    remediation = await rem_service.generate_remediation(
        finding_id=finding_id,
        organization_id=project.organization_id,
        user_id=current_user.id,
        prompt_version=body.prompt_version,
    )

    # Reload with validations eager-loaded
    res = await db.execute(
        select(Remediation)
        .where(Remediation.id == remediation.id)
        .options(selectinload(Remediation.validations))
    )
    full_rem = res.scalar_one()

    return success_response(
        data=RemediationResponse.model_validate(full_rem).model_dump(mode="json"),
        message="Remediation generated successfully",
    )


@router.get("/findings/{finding_id}/verification", summary="Get finding verification status")
async def get_finding_verification(
    finding_id: uuid.UUID,
    finding_context: tuple[Finding, Project, OrganizationMember] = Depends(require_finding_access),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve authoritative verification status and evidence chain for a finding."""
    finding, project, member = finding_context
    _verify_member_permission(member, "finding.read")

    rem_service = RemediationService(db)
    status_data = await rem_service.get_verification_status(
        finding_id=finding_id,
        organization_id=project.organization_id,
    )
    return success_response(
        data=VerificationStatusResponse.model_validate(status_data).model_dump(mode="json"),
        message="Verification status retrieved",
    )


# ── 2. Remediation Lifecycle & Review Endpoints ───────────────


@router.get("/remediations/{remediation_id}", summary="Get remediation details")
async def get_remediation_detail(
    remediation_id: uuid.UUID,
    rem_context: tuple[Any, Project, OrganizationMember] = Depends(require_remediation_access),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve complete remediation details including patch diff and validation attempts."""
    remediation, project, member = rem_context
    _verify_member_permission(member, "remediation.read")

    res = await db.execute(
        select(Remediation)
        .where(Remediation.id == remediation_id)
        .options(selectinload(Remediation.validations))
    )
    full_rem = res.scalar_one_or_none()
    if not full_rem:
        raise NotFoundError("Remediation not found")

    return success_response(
        data=RemediationResponse.model_validate(full_rem).model_dump(mode="json"),
        message="Remediation details retrieved",
    )


@router.post("/remediations/{remediation_id}/review", summary="Review remediation (approve/reject)")
async def review_remediation(
    remediation_id: uuid.UUID,
    body: RemediationReviewRequest,
    rem_context: tuple[Any, Project, OrganizationMember] = Depends(require_remediation_access),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Approve or reject a proposed remediation patch."""
    remediation, project, member = rem_context
    _verify_member_permission(member, "remediation.review")

    rem_service = RemediationService(db)
    updated = await rem_service.review_remediation(
        remediation_id=remediation_id,
        organization_id=project.organization_id,
        user_id=current_user.id,
        decision=body.decision,
        comment=body.comment,
    )

    res = await db.execute(
        select(Remediation)
        .where(Remediation.id == updated.id)
        .options(selectinload(Remediation.validations))
    )
    full_rem = res.scalar_one()

    return success_response(
        data=RemediationResponse.model_validate(full_rem).model_dump(mode="json"),
        message=f"Remediation review recorded ({body.decision.upper()})",
    )


@router.post("/remediations/{remediation_id}/apply", summary="Apply remediation to validation workspace")
async def apply_remediation(
    remediation_id: uuid.UUID,
    rem_context: tuple[Any, Project, OrganizationMember] = Depends(require_remediation_access),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Prepare and apply remediation patch to isolated validation workspace."""
    remediation, project, member = rem_context
    _verify_member_permission(member, "remediation.apply")

    rem_service = RemediationService(db)
    updated = await rem_service.apply_remediation(
        remediation_id=remediation_id,
        organization_id=project.organization_id,
        user_id=current_user.id,
    )

    res = await db.execute(
        select(Remediation)
        .where(Remediation.id == updated.id)
        .options(selectinload(Remediation.validations))
    )
    full_rem = res.scalar_one()

    return success_response(
        data=RemediationResponse.model_validate(full_rem).model_dump(mode="json"),
        message="Remediation applied to validation sandbox",
    )


@router.post("/remediations/{remediation_id}/validate", summary="Execute multi-stage validation")
async def validate_remediation(
    remediation_id: uuid.UUID,
    body: ValidateRemediationRequest = ValidateRemediationRequest(),
    rem_context: tuple[Any, Project, OrganizationMember] = Depends(require_remediation_access),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger isolated multi-stage validation (Syntax, Build, Tests, Static, Taint, Verification Scan)."""
    remediation, project, member = rem_context
    _verify_member_permission(member, "remediation.validate")

    rem_service = RemediationService(db)
    validation = await rem_service.validate_remediation(
        remediation_id=remediation_id,
        organization_id=project.organization_id,
        user_id=current_user.id,
        run_tests=body.run_tests,
        validation_policy=body.validation_policy,
    )

    return success_response(
        data=RemediationValidationResponse.model_validate(validation).model_dump(mode="json"),
        message=f"Validation completed with status: {validation.status}",
    )


# ── 3. Validation History & Details Endpoints ─────────────────


@router.get("/remediations/{remediation_id}/validations", summary="List validation attempts")
async def list_remediation_validations(
    remediation_id: uuid.UUID,
    rem_context: tuple[Any, Project, OrganizationMember] = Depends(require_remediation_access),
    db: AsyncSession = Depends(get_db),
):
    """List historical validation attempts for a specific remediation."""
    remediation, project, member = rem_context
    _verify_member_permission(member, "remediation.read")

    query = (
        select(RemediationValidation)
        .where(
            RemediationValidation.remediation_id == remediation_id,
            RemediationValidation.organization_id == project.organization_id,
        )
        .order_by(desc(RemediationValidation.attempt_number))
    )
    result = await db.execute(query)
    validations = result.scalars().all()

    items = [
        RemediationValidationResponse.model_validate(v).model_dump(mode="json")
        for v in validations
    ]
    return success_response(data=items, message=f"Retrieved {len(items)} validation attempt(s)")


@router.get("/validations/{validation_id}", summary="Get validation attempt details")
async def get_validation_detail(
    validation_id: uuid.UUID,
    val_context: tuple[Any, Project, OrganizationMember] = Depends(require_validation_access),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve detailed execution results for an isolated validation attempt."""
    validation, project, member = val_context
    _verify_member_permission(member, "remediation.read")

    return success_response(
        data=RemediationValidationResponse.model_validate(validation).model_dump(mode="json"),
        message="Validation details retrieved",
    )
