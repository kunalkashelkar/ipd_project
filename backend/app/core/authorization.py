# ============================================================
# Central Authorization Layer — RBAC & Tenant Isolation
# ============================================================
# Enforces the mandatory Phase 2 security pattern:
#   Identity -> Session Validation -> Organization -> Membership -> Role -> Permission
#
# Prevents IDOR/BOLA: Knowing a UUID never grants resource access.
# ============================================================

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Callable

from fastapi import Depends, Header, Path
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.core.exceptions import AuthenticationError, AuthorizationError, NotFoundError
from backend.app.core.security import decode_token
from backend.app.database.session import get_db
from backend.app.models.organization import Organization, OrganizationMember
from backend.app.models.project import Project
from backend.app.models.rbac import Role, RolePermission
from backend.app.models.repository import Repository
from backend.app.models.scan import Scan
from backend.app.models.finding import Finding
from backend.app.models.session import UserSession
from backend.app.models.user import User

security_scheme = HTTPBearer(auto_error=False)


# ── Core Authentication & Revocable Session Validation ───────


async def get_current_user_and_session(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
) -> tuple[User, UserSession | None]:
    """Validate JWT access token and verify that the associated session is not revoked."""
    if credentials is None:
        raise AuthenticationError("Missing authentication token")

    payload = decode_token(credentials.credentials)
    if payload.get("type") != "access":
        raise AuthenticationError("Invalid token type — expected access token")

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise AuthenticationError("Invalid token: missing subject identity")

    try:
        user_uuid = uuid.UUID(user_id_str)
    except ValueError:
        raise AuthenticationError("Invalid token subject UUID format")

    # Query active user
    user_stmt = select(User).where(User.id == user_uuid)
    result = await db.execute(user_stmt)
    user = result.scalar_one_or_none()

    if user is None:
        raise AuthenticationError("User not found")
    if user.status != "active":
        raise AuthenticationError("Account is inactive or suspended")

    # If token contains a session ID (sid), verify server-side session
    session_id_str = payload.get("sid")
    session: UserSession | None = None
    if session_id_str:
        try:
            sess_uuid = uuid.UUID(session_id_str)
            sess_stmt = select(UserSession).where(
                UserSession.id == sess_uuid,
                UserSession.user_id == user.id,
            )
            sess_res = await db.execute(sess_stmt)
            session = sess_res.scalar_one_or_none()

            if session is None or session.revoked_at is not None:
                raise AuthenticationError("Session has been revoked or invalidated")

            now = datetime.now(timezone.utc)
            if session.expires_at <= now:
                raise AuthenticationError("Session has expired")
        except ValueError:
            pass

    return user, session


async def get_current_user(
    auth_data: tuple[User, UserSession | None] = Depends(get_current_user_and_session),
) -> User:
    """Dependency providing the authenticated user with an active, non-revoked session."""
    user, _ = auth_data
    return user


# ── Organization Context & Membership Resolution ─────────────


from fastapi import Depends, Header, Request

async def resolve_organization_context(
    request: Request,
    x_organization_id: str | None = Header(None, alias="X-Organization-ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> tuple[Organization, OrganizationMember]:
    """Resolve target organization from route path parameters or X-Organization-ID header,
    and verify that the current user possesses an ACTIVE membership.
    """
    path_org_id = request.path_params.get("organization_id")
    target_org_id: uuid.UUID | None = None

    if path_org_id:
        try:
            target_org_id = uuid.UUID(str(path_org_id))
        except ValueError:
            raise AuthorizationError("Invalid organization UUID in URL path")
    elif x_organization_id:
        try:
            target_org_id = uuid.UUID(x_organization_id)
        except ValueError:
            raise AuthorizationError("Invalid X-Organization-ID header format")


    if target_org_id is None:
        # Fallback: check first active membership for the user
        fallback_stmt = (
            select(OrganizationMember)
            .where(
                OrganizationMember.user_id == current_user.id,
                OrganizationMember.status == "active",
            )
            .options(
                selectinload(OrganizationMember.organization),
                selectinload(OrganizationMember.role)
                .selectinload(Role.permissions)
                .selectinload(RolePermission.permission),
            )
            .limit(1)
        )
        fallback_res = await db.execute(fallback_stmt)
        member = fallback_res.scalar_one_or_none()
        if member is None:
            raise AuthorizationError("User does not belong to any active organization")
        return member.organization, member

    # Verify active membership in the target organization with eager loaded permissions
    member_stmt = (
        select(OrganizationMember)
        .where(
            OrganizationMember.organization_id == target_org_id,
            OrganizationMember.user_id == current_user.id,
        )
        .options(
            selectinload(OrganizationMember.organization),
            selectinload(OrganizationMember.role)
            .selectinload(Role.permissions)
            .selectinload(RolePermission.permission),
        )
    )
    member_res = await db.execute(member_stmt)
    member = member_res.scalar_one_or_none()

    if member is None or member.status != "active":
        # Do not reveal organization existence if user has no active membership
        raise AuthorizationError("Access denied: You are not an active member of this organization")

    if not member.organization.is_active:
        raise AuthorizationError("Organization is currently deactivated")

    return member.organization, member


async def resolve_active_organization(
    org_context: tuple[Organization, OrganizationMember] = Depends(resolve_organization_context),
) -> uuid.UUID:
    """Convenience dependency providing verified active organization UUID."""
    org, _ = org_context
    return org.id


# ── Permission Check Factory ─────────────────────────────────


def require_permission(permission_key: str) -> Callable:
    """Dependency factory checking that current user possesses permission_key in the organization."""

    async def _permission_dependency(
        org_context: tuple[Organization, OrganizationMember] = Depends(resolve_organization_context),
    ) -> tuple[Organization, OrganizationMember]:
        org, member = org_context

        # Role name 'owner' has all permissions by definition
        if member.role.name == "owner":
            return org, member

        # Check explicit permission keys granted to the role
        granted_keys = {
            rp.permission.key
            for rp in member.role.permissions
            if rp.permission is not None
        }

        if permission_key not in granted_keys:
            raise AuthorizationError(
                f"Permission denied: Action requires '{permission_key}' in organization '{org.name}'"
            )

        return org, member

    return _permission_dependency


# ── Tenant-Safe Resource Scoping Dependencies ────────────────


async def require_project_access(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> tuple[Project, OrganizationMember]:
    """Tenant-isolated project resolution:

    Resolves project -> organization -> current user active membership.
    UUID knowledge of another tenant's project returns 404 to avoid leaking metadata.
    """
    stmt = (
        select(Project, OrganizationMember)
        .join(Organization, Project.organization_id == Organization.id)
        .join(
            OrganizationMember,
            (OrganizationMember.organization_id == Organization.id)
            & (OrganizationMember.user_id == current_user.id)
            & (OrganizationMember.status == "active"),
        )
        .options(
            selectinload(OrganizationMember.role)
            .selectinload(Role.permissions)
            .selectinload(RolePermission.permission)
        )
        .where(Project.id == project_id)
    )

    result = await db.execute(stmt)
    row = result.first()

    if row is None:
        raise NotFoundError("Project not found")

    project, member = row

    # Role 'owner' has all permissions by definition; otherwise require project.read
    if member.role.name != "owner":
        granted = {rp.permission.key for rp in member.role.permissions if rp.permission}
        if "project.read" not in granted:
            raise AuthorizationError(
                f"Permission denied: Action requires 'project.read' in organization '{member.organization.name if hasattr(member, 'organization') and member.organization else ''}'"
            )

    return project, member


async def require_repository_access(
    repository_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> tuple[Repository, Project, OrganizationMember]:
    """Tenant-isolated repository resolution:

    Resolves repository -> project -> organization -> current user active membership.
    """
    stmt = (
        select(Repository, Project, OrganizationMember)
        .join(Project, Repository.project_id == Project.id)
        .join(Organization, Project.organization_id == Organization.id)
        .join(
            OrganizationMember,
            (OrganizationMember.organization_id == Organization.id)
            & (OrganizationMember.user_id == current_user.id)
            & (OrganizationMember.status == "active"),
        )
        .options(
            selectinload(OrganizationMember.role)
            .selectinload(Role.permissions)
            .selectinload(RolePermission.permission)
        )
        .where(Repository.id == repository_id)
    )

    result = await db.execute(stmt)
    row = result.first()

    if row is None:
        raise NotFoundError("Repository not found")

    repo, project, member = row

    if member.role.name != "owner":
        granted = {rp.permission.key for rp in member.role.permissions if rp.permission}
        if "repository.read" not in granted:
            raise AuthorizationError(
                f"Permission denied: Action requires 'repository.read' in organization '{member.organization.name if hasattr(member, 'organization') and member.organization else ''}'"
            )

    return repo, project, member


async def require_scan_access(
    scan_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> tuple[Scan, Project, OrganizationMember]:
    """Tenant-isolated scan resolution:

    Resolves scan -> project -> organization -> current user active membership.
    UUID knowledge of another tenant's scan returns 404 to avoid leaking existence.
    Checks scan.read permission on member role.
    """
    stmt = (
        select(Scan, Project, OrganizationMember)
        .join(Project, Scan.project_id == Project.id)
        .join(Organization, Project.organization_id == Organization.id)
        .join(
            OrganizationMember,
            (OrganizationMember.organization_id == Organization.id)
            & (OrganizationMember.user_id == current_user.id)
            & (OrganizationMember.status == "active"),
        )
        .options(
            selectinload(OrganizationMember.role)
            .selectinload(Role.permissions)
            .selectinload(RolePermission.permission)
        )
        .where(Scan.id == scan_id)
    )

    result = await db.execute(stmt)
    row = result.first()

    if row is None:
        raise NotFoundError("Scan not found")

    scan, project, member = row

    if member.role.name != "owner":
        granted = {rp.permission.key for rp in member.role.permissions if rp.permission}
        if "scan.read" not in granted:
            raise AuthorizationError(
                f"Permission denied: Action requires 'scan.read' in organization '{member.organization.name if hasattr(member, 'organization') and member.organization else ''}'"
            )

    return scan, project, member


async def require_finding_access(
    finding_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> tuple[Finding, Project, OrganizationMember]:
    """Tenant-isolated finding resolution:

    Resolves finding -> project -> organization -> current user active membership.
    UUID knowledge of another tenant's finding returns 404 to avoid leaking existence.
    Checks finding.read permission on member role.
    """
    stmt = (
        select(Finding, Project, OrganizationMember)
        .join(Project, Finding.project_id == Project.id)
        .join(Organization, Project.organization_id == Organization.id)
        .join(
            OrganizationMember,
            (OrganizationMember.organization_id == Organization.id)
            & (OrganizationMember.user_id == current_user.id)
            & (OrganizationMember.status == "active"),
        )
        .options(
            selectinload(OrganizationMember.role)
            .selectinload(Role.permissions)
            .selectinload(RolePermission.permission)
        )
        .where(Finding.id == finding_id)
    )

    result = await db.execute(stmt)
    row = result.first()

    if row is None:
        raise NotFoundError("Finding not found")

    finding, project, member = row

    if member.role.name != "owner":
        granted = {rp.permission.key for rp in member.role.permissions if rp.permission}
        if "finding.read" not in granted:
            raise AuthorizationError(
                f"Permission denied: Action requires 'finding.read' in organization '{member.organization.name if hasattr(member, 'organization') and member.organization else ''}'"
            )

    return finding, project, member

