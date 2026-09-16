# ============================================================
# Phase 2 Organization Router
# ============================================================

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request, status

from backend.app.core.authorization import (
    get_current_user,
    require_permission,
    resolve_organization_context,
)
from backend.app.core.response import success_response
from backend.app.database.session import AsyncSession, get_db
from backend.app.models.organization import Organization, OrganizationMember
from backend.app.models.user import User
from backend.app.repositories.phase2_repositories import MembershipRepository
from backend.app.schemas.phase2_schemas import (
    CreateOrganizationRequest,
    OrganizationResponse,
    UpdateOrganizationRequest,
)
from backend.app.services.organization_service import OrganizationService

router = APIRouter(prefix="/organizations", tags=["Organizations"])


def _get_client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


@router.post("", summary="Create a new organization workspace", status_code=status.HTTP_201_CREATED)
async def create_organization(
    body: CreateOrganizationRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new organization where the creator is granted OWNER role."""
    service = OrganizationService(db)
    org = await service.create_organization(
        user_id=current_user.id,
        name=body.name,
        slug=body.slug,
        description=body.description,
        ip_address=_get_client_ip(request),
    )
    return success_response(
        data=OrganizationResponse.model_validate(org).model_dump(mode="json"),
        message="Organization created successfully",
        status_code=201,
    )


@router.get("", summary="List accessible organizations for authenticated user")
async def list_user_organizations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return all organizations where the user holds an active membership."""
    service = OrganizationService(db)
    orgs = await service.list_user_organizations(current_user.id)
    return success_response(
        data=[OrganizationResponse.model_validate(o).model_dump(mode="json") for o in orgs],
        message="Organizations retrieved",
    )


@router.get("/{organization_id}", summary="Get organization details")
async def get_organization(
    organization_id: uuid.UUID,
    org_context: tuple[Organization, OrganizationMember] = Depends(require_permission("organization.read")),
):
    """Retrieve details for the organization (requires active membership)."""
    org, member = org_context
    setattr(org, "current_user_role", member.role.name if member.role else None)
    return success_response(
        data=OrganizationResponse.model_validate(org).model_dump(mode="json"),
        message="Organization retrieved",
    )


@router.get("/{organization_id}/my-membership", summary="Get current user's membership and role in this organization")
async def get_my_membership(
    organization_id: uuid.UUID,
    org_context: tuple[Organization, OrganizationMember] = Depends(resolve_organization_context),
):
    """Get authoritative active organization role and membership status for the current user."""
    _, member = org_context
    return success_response(
        data={
            "organization_id": str(organization_id),
            "user_id": str(member.user_id),
            "role": member.role.name if member.role else "viewer",
            "status": member.status,
            "joined_at": member.joined_at.isoformat() if member.joined_at else None,
        },
        message="Active membership retrieved",
    )


@router.patch("/{organization_id}", summary="Update organization settings")
async def update_organization(
    organization_id: uuid.UUID,
    body: UpdateOrganizationRequest,
    org_context: tuple[Organization, OrganizationMember] = Depends(require_permission("organization.update")),
    db: AsyncSession = Depends(get_db),
):
    """Update organization name or description (requires organization.update permission)."""
    org, _ = org_context
    if body.name is not None:
        org.name = body.name
    if body.description is not None:
        org.description = body.description

    await db.commit()
    return success_response(
        data=OrganizationResponse.model_validate(org).model_dump(mode="json"),
        message="Organization updated successfully",
    )
