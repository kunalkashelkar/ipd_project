# ============================================================
# Phase 2 Repositories: Organization, Membership, RBAC, Sessions, API Keys
# ============================================================

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.models.api_key import ApiKey
from backend.app.models.organization import (
    Organization,
    OrganizationInvitation,
    OrganizationMember,
)
from backend.app.models.rbac import Permission, Role, RolePermission
from backend.app.models.session import UserSession, VerificationToken


class OrganizationRepository:
    """Data access for organizations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, org_id: uuid.UUID) -> Organization | None:
        stmt = select(Organization).where(Organization.id == org_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Organization | None:
        stmt = select(Organization).where(Organization.slug == slug)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, name: str, slug: str, description: str | None = None) -> Organization:
        org = Organization(name=name, slug=slug, description=description, is_active=True)
        self.db.add(org)
        await self.db.flush()
        return org

    async def list_for_user(self, user_id: uuid.UUID) -> Sequence[Organization]:
        stmt = (
            select(Organization, Role.name.label("role_name"))
            .join(OrganizationMember, Organization.id == OrganizationMember.organization_id)
            .join(Role, OrganizationMember.role_id == Role.id)
            .where(
                OrganizationMember.user_id == user_id,
                OrganizationMember.status == "active",
                Organization.is_active == True,  # noqa: E712
            )
            .order_by(Organization.name)
        )
        result = await self.db.execute(stmt)
        orgs = []
        for org, role_name in result.all():
            setattr(org, "current_user_role", role_name)
            orgs.append(org)
        return orgs


class MembershipRepository:
    """Data access for organization memberships and invitations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_membership(self, org_id: uuid.UUID, user_id: uuid.UUID) -> OrganizationMember | None:
        stmt = (
            select(OrganizationMember)
            .where(
                OrganizationMember.organization_id == org_id,
                OrganizationMember.user_id == user_id,
            )
            .options(
                selectinload(OrganizationMember.role),
                selectinload(OrganizationMember.user),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_membership(
        self, org_id: uuid.UUID, user_id: uuid.UUID, role_id: uuid.UUID, status: str = "active"
    ) -> OrganizationMember:
        member = OrganizationMember(
            organization_id=org_id,
            user_id=user_id,
            role_id=role_id,
            status=status,
        )
        self.db.add(member)
        await self.db.flush()
        return member

    async def list_members(self, org_id: uuid.UUID) -> Sequence[OrganizationMember]:
        stmt = (
            select(OrganizationMember)
            .where(OrganizationMember.organization_id == org_id)
            .options(
                selectinload(OrganizationMember.role),
                selectinload(OrganizationMember.user),
            )
            .order_by(OrganizationMember.joined_at)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def count_active_owners(self, org_id: uuid.UUID) -> int:
        """Count the number of active members with the owner role."""
        stmt = (
            select(func.count(OrganizationMember.id))
            .join(Role, OrganizationMember.role_id == Role.id)
            .where(
                OrganizationMember.organization_id == org_id,
                OrganizationMember.status == "active",
                Role.name == "owner",
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one() or 0

    async def create_invitation(
        self,
        org_id: uuid.UUID,
        invited_email: str,
        role_id: uuid.UUID,
        token_hash: str,
        inviter_id: uuid.UUID,
        expires_at: datetime,
    ) -> OrganizationInvitation:
        invitation = OrganizationInvitation(
            organization_id=org_id,
            invited_email=invited_email.lower().strip(),
            role_id=role_id,
            token_hash=token_hash,
            inviter_id=inviter_id,
            status="pending",
            expires_at=expires_at,
        )
        self.db.add(invitation)
        await self.db.flush()
        return invitation

    async def get_invitation_by_hash(self, token_hash: str) -> OrganizationInvitation | None:
        stmt = (
            select(OrganizationInvitation)
            .where(OrganizationInvitation.token_hash == token_hash)
            .options(
                selectinload(OrganizationInvitation.organization),
                selectinload(OrganizationInvitation.role),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_invitations(self, org_id: uuid.UUID) -> Sequence[OrganizationInvitation]:
        stmt = (
            select(OrganizationInvitation)
            .where(OrganizationInvitation.organization_id == org_id)
            .options(selectinload(OrganizationInvitation.role))
            .order_by(OrganizationInvitation.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()


class RbacRepository:
    """Data access for Roles and Permissions."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_role_by_name(self, name: str) -> Role | None:
        stmt = (
            select(Role)
            .where(Role.name == name.lower())
            .options(selectinload(Role.permissions))
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_role_by_id(self, role_id: uuid.UUID) -> Role | None:
        stmt = (
            select(Role)
            .where(Role.id == role_id)
            .options(selectinload(Role.permissions))
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_roles(self) -> Sequence[Role]:
        stmt = select(Role).order_by(Role.name)
        result = await self.db.execute(stmt)
        return result.scalars().all()


class SessionRepository:
    """Data access for revocable server-side user sessions."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_session(
        self,
        user_id: uuid.UUID,
        token_hash: str,
        expires_at: datetime,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> UserSession:
        session = UserSession(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        self.db.add(session)
        await self.db.flush()
        return session

    async def get_by_token_hash(self, token_hash: str) -> UserSession | None:
        stmt = select(UserSession).where(UserSession.token_hash == token_hash)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def revoke_session(self, session_id: uuid.UUID) -> None:
        now = datetime.now(timezone.utc)
        stmt = (
            update(UserSession)
            .where(UserSession.id == session_id)
            .values(revoked_at=now)
        )
        await self.db.execute(stmt)

    async def revoke_all_user_sessions(self, user_id: uuid.UUID) -> None:
        now = datetime.now(timezone.utc)
        stmt = (
            update(UserSession)
            .where(UserSession.user_id == user_id, UserSession.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        await self.db.execute(stmt)


class ApiKeyRepository:
    """Data access for organization API keys."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_api_key(
        self,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
        name: str,
        key_prefix: str,
        key_hash: str,
        expires_at: datetime | None = None,
    ) -> ApiKey:
        api_key = ApiKey(
            organization_id=org_id,
            user_id=user_id,
            name=name,
            key_prefix=key_prefix,
            key_hash=key_hash,
            expires_at=expires_at,
        )
        self.db.add(api_key)
        await self.db.flush()
        return api_key

    async def list_for_org(self, org_id: uuid.UUID) -> Sequence[ApiKey]:
        stmt = (
            select(ApiKey)
            .where(ApiKey.organization_id == org_id)
            .order_by(ApiKey.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_by_id(self, key_id: uuid.UUID, org_id: uuid.UUID) -> ApiKey | None:
        stmt = select(ApiKey).where(ApiKey.id == key_id, ApiKey.organization_id == org_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def revoke_api_key(self, key_id: uuid.UUID, org_id: uuid.UUID) -> None:
        now = datetime.now(timezone.utc)
        stmt = (
            update(ApiKey)
            .where(ApiKey.id == key_id, ApiKey.organization_id == org_id)
            .values(revoked_at=now)
        )
        await self.db.execute(stmt)


class VerificationTokenRepository:
    """Data access for email verification and password reset tokens."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_token(
        self,
        user_id: uuid.UUID,
        token_type: str,
        token_hash: str,
        expires_at: datetime,
    ) -> VerificationToken:
        token = VerificationToken(
            user_id=user_id,
            token_type=token_type,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self.db.add(token)
        await self.db.flush()
        return token

    async def get_valid_token(self, token_hash: str, token_type: str) -> VerificationToken | None:
        now = datetime.now(timezone.utc)
        stmt = select(VerificationToken).where(
            VerificationToken.token_hash == token_hash,
            VerificationToken.token_type == token_type,
            VerificationToken.used_at.is_(None),
            VerificationToken.expires_at > now,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def mark_as_used(self, token_id: uuid.UUID) -> None:
        now = datetime.now(timezone.utc)
        stmt = (
            update(VerificationToken)
            .where(VerificationToken.id == token_id)
            .values(used_at=now)
        )
        await self.db.execute(stmt)
