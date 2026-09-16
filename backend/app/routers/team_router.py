# ============================================================
# Phase 2 Team & Membership Router
# ============================================================

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request, status

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.app.core.authorization import (
    get_current_user,
    require_permission,
    resolve_organization_context,
)
from backend.app.core.response import success_response
from backend.app.database.session import AsyncSession, get_db
from backend.app.models.organization import Organization, OrganizationMember
from backend.app.models.rbac import Role, RolePermission
from backend.app.models.user import User
from backend.app.repositories.phase2_repositories import MembershipRepository
from backend.app.schemas.phase2_schemas import (
    AcceptInvitationRequest,
    ChangeMemberRoleRequest,
    InviteMemberRequest,
    OrganizationInvitationResponse,
    OrganizationMemberResponse,
    RoleWithPermissionsResponse,
)
from backend.app.services.organization_service import OrganizationService

router = APIRouter(prefix="/organizations/{organization_id}/team", tags=["Team Management"])


def _get_client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


@router.get("/members", summary="List members of the organization")
async def list_members(
    organization_id: uuid.UUID,
    org_context: tuple[Organization, OrganizationMember] = Depends(require_permission("team.read")),
    db: AsyncSession = Depends(get_db),
):
    """List all members and their roles within the organization."""
    repo = MembershipRepository(db)
    members = await repo.list_members(organization_id)

    data = [
        OrganizationMemberResponse(
            id=m.id,
            user_id=m.user_id,
            user_name=m.user.name if m.user else "Unknown",
            user_email=m.user.email if m.user else "",
            role=m.role.name if m.role else "unknown",
            status=m.status,
            joined_at=m.joined_at,
        ).model_dump(mode="json")
        for m in members
        if m.status != "removed"
    ]
    return success_response(data=data, message="Members retrieved")


@router.post("/invitations", summary="Invite a new member to the organization", status_code=status.HTTP_201_CREATED)
async def invite_member(
    organization_id: uuid.UUID,
    body: InviteMemberRequest,
    request: Request,
    org_context: tuple[Organization, OrganizationMember] = Depends(require_permission("team.invite")),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Issue a secure invitation token to add a member with a specific role."""
    service = OrganizationService(db)
    invitation, raw_token = await service.invite_member(
        org_id=organization_id,
        inviter_id=current_user.id,
        email=body.email,
        role_name=body.role_name,
        ip_address=_get_client_ip(request),
    )

    resp_data = OrganizationInvitationResponse(
        id=invitation.id,
        organization_id=invitation.organization_id,
        invited_email=invitation.invited_email,
        role_name=body.role_name,
        status=invitation.status,
        expires_at=invitation.expires_at,
        created_at=invitation.created_at,
    ).model_dump(mode="json")
    resp_data["invitation_token"] = raw_token  # Returned once for delivery

    return success_response(
        data=resp_data,
        message="Invitation created successfully",
        status_code=201,
    )


@router.get("/invitations", summary="List pending invitations for the organization")
async def list_invitations(
    organization_id: uuid.UUID,
    org_context: tuple[Organization, OrganizationMember] = Depends(require_permission("team.read")),
    db: AsyncSession = Depends(get_db),
):
    """List pending invitations (does not expose raw tokens)."""
    repo = MembershipRepository(db)
    invitations = await repo.list_invitations(organization_id)

    data = [
        OrganizationInvitationResponse(
            id=inv.id,
            organization_id=inv.organization_id,
            invited_email=inv.invited_email,
            role_name=inv.role.name if inv.role else "unknown",
            status=inv.status,
            expires_at=inv.expires_at,
            created_at=inv.created_at,
        ).model_dump(mode="json")
        for inv in invitations
        if inv.status == "pending"
    ]
    return success_response(data=data, message="Invitations retrieved")


@router.patch("/members/{member_user_id}/role", summary="Change a member's role")
async def change_member_role(
    organization_id: uuid.UUID,
    member_user_id: uuid.UUID,
    body: ChangeMemberRoleRequest,
    request: Request,
    org_context: tuple[Organization, OrganizationMember] = Depends(require_permission("team.role.update")),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change member role enforcing owner protections."""
    service = OrganizationService(db)
    updated = await service.change_member_role(
        org_id=organization_id,
        actor_id=current_user.id,
        target_user_id=member_user_id,
        new_role_name=body.role_name,
        ip_address=_get_client_ip(request),
    )
    return success_response(
        data=OrganizationMemberResponse(
            id=updated.id,
            user_id=updated.user_id,
            user_name=updated.user.name if updated.user else "Unknown",
            user_email=updated.user.email if updated.user else "",
            role=updated.role.name if updated.role else body.role_name,
            status=updated.status,
            joined_at=updated.joined_at,
        ).model_dump(mode="json"),
        message="Member role updated",
    )


@router.delete("/members/{member_user_id}", summary="Remove a member from the organization")
async def remove_member(
    organization_id: uuid.UUID,
    member_user_id: uuid.UUID,
    request: Request,
    org_context: tuple[Organization, OrganizationMember] = Depends(require_permission("team.remove")),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove member while preserving audit logs and scan history."""
    service = OrganizationService(db)
    await service.remove_member(
        org_id=organization_id,
        actor_id=current_user.id,
        target_user_id=member_user_id,
        ip_address=_get_client_ip(request),
    )
    return success_response(data=None, message="Member removed from organization")


@router.get("/roles", summary="List predefined roles and their detailed permissions")
async def list_roles(
    organization_id: uuid.UUID,
    org_context: tuple[Organization, OrganizationMember] = Depends(require_permission("team.read")),
    db: AsyncSession = Depends(get_db),
):
    """Return authoritative list of system roles and their assigned permissions."""
    stmt = (
        select(Role)
        .options(
            selectinload(Role.permissions).selectinload(RolePermission.permission)
        )
        .order_by(Role.name)
    )
    result = await db.execute(stmt)
    roles = result.scalars().all()
    data = []
    for r in roles:
        data.append({
            "id": r.id,
            "name": r.name,
            "description": r.description,
            "permissions": [
                {
                    "id": rp.permission.id,
                    "key": rp.permission.key,
                    "description": rp.permission.description,
                    "category": rp.permission.category,
                }
                for rp in r.permissions if rp.permission
            ]
        })
    return success_response(data=data, message="Roles and permissions retrieved")


# Standalone route for accepting an invitation: /api/v1/invitations/accept
invitation_router = APIRouter(prefix="/invitations", tags=["Invitations"])


@invitation_router.get("/{token}", summary="Get invitation details by token")
async def get_invitation_details(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """View details of a pending invitation before accepting."""
    service = OrganizationService(db)
    details = await service.get_invitation_details(token)
    return success_response(data=details, message="Invitation details retrieved")


@invitation_router.post("/accept", summary="Accept an organization invitation")
async def accept_invitation(
    body: AcceptInvitationRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Join an organization by providing a valid invitation token."""
    service = OrganizationService(db)
    member = await service.accept_invitation(
        raw_token=body.token,
        user_id=current_user.id,
        ip_address=_get_client_ip(request),
    )
    return success_response(
        data=OrganizationMemberResponse(
            id=member.id,
            user_id=member.user_id,
            user_name=current_user.name,
            user_email=current_user.email,
            role=member.role.name if member.role else "member",
            status=member.status,
            joined_at=member.joined_at,
        ).model_dump(mode="json"),
        message="Invitation accepted successfully",
    )
