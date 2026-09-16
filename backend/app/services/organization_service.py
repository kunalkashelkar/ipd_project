# ============================================================
# Phase 2 Organization & Team Management Service
# ============================================================

from __future__ import annotations

import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import ConflictError, NotFoundError, ValidationError
from backend.app.core.security import generate_secure_token, hash_token
from backend.app.models.organization import (
    Organization,
    OrganizationInvitation,
    OrganizationMember,
)
from backend.app.repositories.audit_repository import AuditRepository
from backend.app.repositories.phase2_repositories import (
    MembershipRepository,
    OrganizationRepository,
    RbacRepository,
)
from backend.app.repositories.user_repository import UserRepository


class OrganizationService:
    """Business logic for organization workspaces and team membership."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.org_repo = OrganizationRepository(db)
        self.membership_repo = MembershipRepository(db)
        self.rbac_repo = RbacRepository(db)
        self.user_repo = UserRepository(db)
        self.audit_repo = AuditRepository(db)

    def _generate_slug(self, name: str) -> str:
        """Create a URL-safe slug from an organization name."""
        base_slug = re.sub(r"[^a-zA-Z0-9]+", "-", name.lower()).strip("-")
        return base_slug[:80] or "workspace"

    async def create_organization(
        self,
        *,
        user_id: uuid.UUID,
        name: str,
        slug: str | None = None,
        description: str | None = None,
        ip_address: str | None = None,
    ) -> Organization:
        """Create a new organization and assign the creator as OWNER."""
        resolved_slug = slug or self._generate_slug(name)

        # Check slug availability
        existing = await self.org_repo.get_by_slug(resolved_slug)
        if existing:
            resolved_slug = f"{resolved_slug}-{uuid.uuid4().hex[:6]}"

        org = await self.org_repo.create(name=name, slug=resolved_slug, description=description)

        # Resolve OWNER role
        owner_role = await self.rbac_repo.get_role_by_name("owner")
        if not owner_role:
            raise ValidationError("System 'owner' role not initialized in database")

        # Assign creator as Owner
        await self.membership_repo.create_membership(
            org_id=org.id,
            user_id=user_id,
            role_id=owner_role.id,
            status="active",
        )

        # Audit event
        await self.audit_repo.log_action(
            user_id=user_id,
            action="organization.created",
            resource_type="organization",
            resource_id=str(org.id),
            ip_address=ip_address,
            metadata={"name": name, "slug": resolved_slug},
        )

        await self.db.commit()
        return org

    async def list_user_organizations(self, user_id: uuid.UUID) -> Sequence[Organization]:
        return await self.org_repo.list_for_user(user_id)

    async def invite_member(
        self,
        *,
        org_id: uuid.UUID,
        inviter_id: uuid.UUID,
        email: str,
        role_name: str,
        ip_address: str | None = None,
    ) -> tuple[OrganizationInvitation, str]:
        """Create a secure expiring invitation to join an organization."""
        normalized_email = email.lower().strip()

        # Role validation: cannot invite as 'owner' directly
        if role_name.lower() == "owner":
            raise ValidationError("Direct invitation with 'owner' role is forbidden")

        role = await self.rbac_repo.get_role_by_name(role_name)
        if not role:
            raise NotFoundError(f"Role '{role_name}' does not exist")

        # Check if already an active member
        existing_user = await self.user_repo.get_by_email(normalized_email)
        if existing_user:
            existing_member = await self.membership_repo.get_membership(org_id, existing_user.id)
            if existing_member and existing_member.status == "active":
                raise ConflictError("User is already an active member of this organization")

        # Generate secure random invitation token
        raw_token = generate_secure_token(32)
        token_hash = hash_token(raw_token)
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)

        invitation = await self.membership_repo.create_invitation(
            org_id=org_id,
            invited_email=normalized_email,
            role_id=role.id,
            token_hash=token_hash,
            inviter_id=inviter_id,
            expires_at=expires_at,
        )

        # Audit event (never log raw token)
        await self.audit_repo.log_action(
            user_id=inviter_id,
            action="team.member_invited",
            resource_type="organization",
            resource_id=str(org_id),
            ip_address=ip_address,
            metadata={"invited_email": normalized_email, "role": role_name},
        )

        await self.db.commit()
        return invitation, raw_token

    async def accept_invitation(
        self,
        *,
        raw_token: str,
        user_id: uuid.UUID,
        ip_address: str | None = None,
    ) -> OrganizationMember:
        """Accept an invitation and instantiate active membership for authenticated user."""
        token_hash = hash_token(raw_token)
        invitation = await self.membership_repo.get_invitation_by_hash(token_hash)

        if not invitation:
            raise NotFoundError("Invalid or expired invitation token")

        now = datetime.now(timezone.utc)
        if invitation.status != "pending" or invitation.expires_at <= now:
            raise ValidationError("Invitation is no longer valid or has expired")

        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")

        # Verify email matches invited email
        if user.email.lower() != invitation.invited_email.lower():
            raise ValidationError("Invitation was issued to a different email address")

        # Check or create membership
        member = await self.membership_repo.get_membership(invitation.organization_id, user.id)
        if member:
            member.status = "active"
            member.role_id = invitation.role_id
            member.role = invitation.role
        else:
            member = await self.membership_repo.create_membership(
                org_id=invitation.organization_id,
                user_id=user.id,
                role_id=invitation.role_id,
                status="active",
            )
            member.role = invitation.role

        # Invalidate invitation
        invitation.status = "accepted"
        invitation.accepted_at = now

        # Audit event
        await self.audit_repo.log_action(
            user_id=user.id,
            action="team.invitation_accepted",
            resource_type="organization",
            resource_id=str(invitation.organization_id),
            ip_address=ip_address,
        )

        await self.db.commit()
        # Reload with selectinload so relationships are cleanly populated
        reloaded_member = await self.membership_repo.get_membership(invitation.organization_id, user.id)
        return reloaded_member  # type: ignore[return-value]

    async def change_member_role(
        self,
        *,
        org_id: uuid.UUID,
        actor_id: uuid.UUID,
        target_user_id: uuid.UUID,
        new_role_name: str,
        ip_address: str | None = None,
    ) -> OrganizationMember:
        """Change a member's role while enforcing owner invariants."""
        target_member = await self.membership_repo.get_membership(org_id, target_user_id)
        if not target_member or target_member.status != "active":
            raise NotFoundError("Member not found in organization")

        new_role = await self.rbac_repo.get_role_by_name(new_role_name)
        if not new_role:
            raise NotFoundError(f"Role '{new_role_name}' does not exist")

        # INVARIANT: Prevent demoting the final owner
        if target_member.role.name == "owner" and new_role.name != "owner":
            owner_count = await self.membership_repo.count_active_owners(org_id)
            if owner_count <= 1:
                raise ValidationError(
                    "Cannot demote the sole organization owner. Transfer ownership or assign another owner first."
                )

        old_role_name = target_member.role.name
        target_member.role_id = new_role.id
        target_member.role = new_role

        await self.audit_repo.log_action(
            user_id=actor_id,
            action="team.role_changed",
            resource_type="organization_member",
            resource_id=str(target_member.id),
            ip_address=ip_address,
            metadata={
                "target_user_id": str(target_user_id),
                "old_role": old_role_name,
                "new_role": new_role_name,
            },
        )

        await self.db.commit()
        reloaded_member = await self.membership_repo.get_membership(org_id, target_user_id)
        return reloaded_member  # type: ignore[return-value]

    async def remove_member(
        self,
        *,
        org_id: uuid.UUID,
        actor_id: uuid.UUID,
        target_user_id: uuid.UUID,
        ip_address: str | None = None,
    ) -> None:
        """Remove a member from the organization while preserving audit history."""
        target_member = await self.membership_repo.get_membership(org_id, target_user_id)
        if not target_member or target_member.status != "active":
            raise NotFoundError("Member not found in organization")

        # INVARIANT: Cannot remove the final owner
        if target_member.role.name == "owner":
            owner_count = await self.membership_repo.count_active_owners(org_id)
            if owner_count <= 1:
                raise ValidationError("Cannot remove the sole organization owner.")

        # Soft-remove: update status to 'removed' to preserve historical scans and audit history
        target_member.status = "removed"

        await self.audit_repo.log_action(
            user_id=actor_id,
            action="team.member_removed",
            resource_type="organization_member",
            resource_id=str(target_member.id),
            ip_address=ip_address,
            metadata={"target_user_id": str(target_user_id)},
        )

        await self.db.commit()

    async def get_invitation_details(self, raw_token: str) -> dict:
        """Fetch invitation details by raw token for previewing before acceptance."""
        token_hash = hash_token(raw_token)
        invitation = await self.membership_repo.get_invitation_by_hash(token_hash)
        if not invitation:
            raise NotFoundError("Invalid or expired invitation token")
        now = datetime.now(timezone.utc)
        if invitation.status != "pending" or invitation.expires_at <= now:
            raise ValidationError("Invitation is no longer valid or has expired")
        existing_user = await self.user_repo.get_by_email(invitation.invited_email.lower().strip())
        already_member = False
        if existing_user:
            existing_member = await self.membership_repo.get_membership(invitation.organization_id, existing_user.id)
            already_member = existing_member is not None and existing_member.status == "active"

        return {
            "id": str(invitation.id),
            "organization_id": str(invitation.organization_id),
            "organization_name": invitation.organization.name if invitation.organization else "Workspace",
            "invited_email": invitation.invited_email,
            "role_name": invitation.role.name if invitation.role else "viewer",
            "expires_at": invitation.expires_at.isoformat(),
            "status": invitation.status,
            "account_exists": existing_user is not None,
            "already_member": already_member,
        }

