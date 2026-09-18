# ============================================================
# XAI Router — Explainability & Attribution APIs (Phase 6)
# ============================================================
# Tenant-safe REST endpoints for evidence-aware vulnerability explanations
# and normalized attribution (Captum/IG, SHAP, GNNExplainer, Attention).
# ============================================================

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.authorization import (
    get_current_user,
    require_finding_access,
)
from backend.app.core.exceptions import AuthorizationError, NotFoundError
from backend.app.core.response import success_response
from backend.app.database.session import get_db
from backend.app.models.explanation import AIExplanation
from backend.app.models.finding import Finding
from backend.app.models.organization import OrganizationMember
from backend.app.models.project import Project
from backend.app.models.user import User
from backend.app.schemas.xai_schemas import GenerateExplanationRequest, XAIExplanationResponse
from backend.app.services.audit_service import AuditService
from backend.app.services.xai.service import XAIExplanationService

router = APIRouter(tags=["XAI Explanations"])


def _verify_member_permission(member: OrganizationMember, required_key: str) -> None:
    if member.role.name == "owner":
        return
    granted = {rp.permission.key for rp in member.role.permissions if rp.permission}
    if required_key not in granted:
        raise AuthorizationError(f"Permission denied: Action requires '{required_key}'")


@router.get("/findings/{finding_id}/explanation", summary="Get finding explanations")
async def get_finding_explanations(
    finding_id: uuid.UUID,
    method: str | None = Query(None, description="Optional filter by explanation method"),
    finding_context: tuple[Finding, Project, OrganizationMember] = Depends(require_finding_access),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve persisted AI explanations and normalized attribution for a finding."""
    finding, project, member = finding_context
    _verify_member_permission(member, "explanation.read")

    query = select(AIExplanation).where(
        AIExplanation.finding_id == finding_id,
        AIExplanation.organization_id == project.organization_id,
    )
    if method:
        query = query.where(AIExplanation.explanation_method == method)
    query = query.order_by(desc(AIExplanation.created_at))

    result = await db.execute(query)
    explanations = result.scalars().all()

    items = [
        XAIExplanationResponse.model_validate(e).model_dump(mode="json")
        for e in explanations
    ]
    return success_response(data=items, message=f"Retrieved {len(items)} explanations")


@router.post("/findings/{finding_id}/explanation", summary="Generate finding explanation")
async def generate_finding_explanation(
    finding_id: uuid.UUID,
    body: GenerateExplanationRequest = GenerateExplanationRequest(),
    finding_context: tuple[Finding, Project, OrganizationMember] = Depends(require_finding_access),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a structured, evidence-aware explanation or XAI attribution for a finding."""
    finding, project, member = finding_context
    _verify_member_permission(member, "explanation.generate")

    xai_service = XAIExplanationService(db)
    explanation_record = await xai_service.generate_explanation(
        finding_id=finding_id,
        organization_id=project.organization_id,
        user_id=current_user.id,
        method=body.method,
    )

    audit = AuditService(db)
    await audit.log(
        user_id=current_user.id,
        action="explanation_generated",
        resource_type="finding",
        resource_id=str(finding_id),
        metadata={
            "explanation_id": str(explanation_record.id),
            "method": body.method,
            "method_status": explanation_record.method_status,
        },
    )
    await db.commit()

    return success_response(
        data=XAIExplanationResponse.model_validate(explanation_record).model_dump(mode="json"),
        message=f"Explanation generated via {body.method}",
    )
