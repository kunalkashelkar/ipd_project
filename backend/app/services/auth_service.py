# ============================================================
# Phase 2 Auth Service — Multi-Tenant Identity & Sessions
# ============================================================

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import get_settings
from backend.app.core.exceptions import (
    AuthenticationError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from backend.app.core.security import (
    create_token_pair,
    decode_token,
    generate_secure_token,
    hash_password,
    hash_token,
    verify_password,
)
from backend.app.models.user import User
from backend.app.repositories.audit_repository import AuditRepository
from backend.app.repositories.phase2_repositories import (
    MembershipRepository,
    OrganizationRepository,
    RbacRepository,
    SessionRepository,
    VerificationTokenRepository,
)
from backend.app.repositories.user_repository import UserRepository


class AuthService:
    """Handles multi-tenant identity, authentication, revocable sessions, and tokens."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)
        self.org_repo = OrganizationRepository(db)
        self.membership_repo = MembershipRepository(db)
        self.rbac_repo = RbacRepository(db)
        self.session_repo = SessionRepository(db)
        self.verification_repo = VerificationTokenRepository(db)
        self.audit_repo = AuditRepository(db)

    async def register(
        self,
        *,
        name: str,
        email: str,
        password: str,
        organization_name: str | None = None,
        invitation_token: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict:
        """Atomic registration:

        If invitation_token is supplied:
          1. Validates invitation token against database.
          2. Verifies invited_email matches email.
          3. Creates User identity.
          4. Directly assigns user as active member of the invited Organization with the invited Role.
          5. Marks invitation as accepted.
          6. Creates active session scoped to the invited Organization.
        Otherwise:
          1. Creates User identity.
          2. Creates dedicated Organization workspace where user is Owner.
          3. Creates active server-side session.
        """
        normalized_email = email.lower().strip()

        if await self.user_repo.email_exists(normalized_email):
            raise ConflictError("Email is already registered. Please sign in to access your workspace.")

        invitation = None
        if invitation_token:
            token_hash = hash_token(invitation_token)
            invitation = await self.membership_repo.get_invitation_by_hash(token_hash)
            if not invitation:
                raise NotFoundError("Invalid or expired invitation token")
            now = datetime.now(timezone.utc)
            if invitation.status != "pending" or invitation.expires_at <= now:
                raise ValidationError("Invitation is no longer valid or has expired")
            if normalized_email != invitation.invited_email.lower().strip():
                raise ValidationError("Registration email must match the invited email address")

        # 1. Create User
        user = await self.user_repo.create(
            name=name,
            email=normalized_email,
            password_hash=hash_password(password),
            role="researcher",  # Legacy column
            status="active",
        )

        if invitation:
            # Join invited organization with designated role
            org = invitation.organization
            await self.membership_repo.create_membership(
                org_id=invitation.organization_id,
                user_id=user.id,
                role_id=invitation.role_id,
                status="active",
            )
            invitation.status = "accepted"
            invitation.accepted_at = datetime.now(timezone.utc)

            await self.audit_repo.log_action(
                user_id=user.id,
                organization_id=invitation.organization_id,
                action="user.registered",
                resource_type="user",
                resource_id=str(user.id),
                ip_address=ip_address,
                metadata={"via_invitation": True},
            )
            await self.audit_repo.log_action(
                user_id=user.id,
                organization_id=invitation.organization_id,
                action="team.invitation_accepted",
                resource_type="organization",
                resource_id=str(invitation.organization_id),
                ip_address=ip_address,
            )
            active_org_id = invitation.organization_id
        else:
            # 2. Create Organization
            org_title = organization_name or f"{name.split()[0]}'s Workspace"
            base_slug = "".join(c for c in org_title.lower().replace(" ", "-") if c.isalnum() or c == "-")[:80] or "workspace"
            slug = f"{base_slug}-{uuid.uuid4().hex[:6]}"

            org = await self.org_repo.create(name=org_title, slug=slug)

            # 3. Assign Owner Role in Organization
            owner_role = await self.rbac_repo.get_role_by_name("owner")
            if not owner_role:
                raise ValidationError("System 'owner' role not found in database")

            await self.membership_repo.create_membership(
                org_id=org.id,
                user_id=user.id,
                role_id=owner_role.id,
                status="active",
            )

            # Audit log
            await self.audit_repo.log_action(
                user_id=user.id,
                organization_id=org.id,
                action="user.registered",
                resource_type="user",
                resource_id=str(user.id),
                ip_address=ip_address,
            )
            active_org_id = org.id

        # 4. Create Session
        raw_refresh = generate_secure_token(32)
        token_hash = hash_token(raw_refresh)
        settings = get_settings()
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)

        session = await self.session_repo.create_session(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
        )

        await self.db.commit()

        # Generate tokens linked to server session
        tokens = create_token_pair(
            user_id=str(user.id),
            email=user.email,
            session_id=str(session.id),
            active_org_id=str(active_org_id),
        )
        tokens["refresh_token"] = raw_refresh

        return {
            "user": user,
            "organization": org,
            "tokens": tokens,
        }

    async def login(
        self,
        *,
        email: str,
        password: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict:
        """Authenticate credentials, create server-side session, and issue tokens."""
        normalized_email = email.lower().strip()
        user = await self.user_repo.get_by_email(normalized_email)

        if user is None or not verify_password(password, user.password_hash):
            await self.audit_repo.log_action(
                user_id=user.id if user else None,
                action="user.login_failed",
                resource_type="user",
                ip_address=ip_address,
                user_agent=user_agent,
                metadata={"email": normalized_email},
            )
            raise AuthenticationError("Invalid email or password")

        if user.status != "active":
            raise AuthenticationError("Account is inactive or suspended")

        await self.user_repo.update_last_login(user)

        # Resolve user's organizations
        orgs = await self.org_repo.list_for_user(user.id)
        active_org = orgs[0] if orgs else None

        # Create server-side session
        raw_refresh = generate_secure_token(32)
        token_hash = hash_token(raw_refresh)
        settings = get_settings()
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)

        session = await self.session_repo.create_session(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
        )

        await self.audit_repo.log_action(
            user_id=user.id,
            organization_id=active_org.id if active_org else None,
            action="user.login",
            resource_type="user",
            resource_id=str(user.id),
            ip_address=ip_address,
            user_agent=user_agent,
        )

        await self.db.commit()

        tokens = create_token_pair(
            user_id=str(user.id),
            email=user.email,
            session_id=str(session.id),
            active_org_id=str(active_org.id) if active_org else None,
        )
        tokens["refresh_token"] = raw_refresh

        return {
            "user": user,
            "organizations": orgs,
            "active_organization": active_org,
            "tokens": tokens,
        }

    async def logout(self, session_id: uuid.UUID | None, user_id: uuid.UUID, ip_address: str | None = None) -> None:
        """Revoke the active server session."""
        if session_id:
            await self.session_repo.revoke_session(session_id)

        await self.audit_repo.log_action(
            user_id=user_id,
            action="user.logout",
            resource_type="user",
            resource_id=str(user_id),
            ip_address=ip_address,
        )
        await self.db.commit()

    async def refresh_session(self, raw_refresh_token: str, user_agent: str | None = None, ip_address: str | None = None) -> dict:
        """Rotate refresh token and issue new access token."""
        token_hash = hash_token(raw_refresh_token)
        session = await self.session_repo.get_by_token_hash(token_hash)

        if not session or session.revoked_at is not None:
            raise AuthenticationError("Invalid or revoked session")

        now = datetime.now(timezone.utc)
        if session.expires_at <= now:
            raise AuthenticationError("Session has expired")

        user = await self.user_repo.get_by_id(session.user_id)
        if not user or user.status != "active":
            raise AuthenticationError("User account is inactive")

        # Refresh token rotation
        new_raw_refresh = generate_secure_token(32)
        session.token_hash = hash_token(new_raw_refresh)
        session.last_used_at = now
        settings = get_settings()
        session.expires_at = now + timedelta(days=settings.refresh_token_expire_days)

        orgs = await self.org_repo.list_for_user(user.id)
        active_org = orgs[0] if orgs else None

        await self.db.commit()

        tokens = create_token_pair(
            user_id=str(user.id),
            email=user.email,
            session_id=str(session.id),
            active_org_id=str(active_org.id) if active_org else None,
        )
        tokens["refresh_token"] = new_raw_refresh

        return {"user": user, "tokens": tokens}

    async def request_password_reset(self, email: str, ip_address: str | None = None) -> str | None:
        """Generate a password reset token (does not reveal account existence to caller)."""
        normalized_email = email.lower().strip()
        user = await self.user_repo.get_by_email(normalized_email)
        if not user or user.status != "active":
            return None

        raw_token = generate_secure_token(32)
        token_hash = hash_token(raw_token)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=2)

        await self.verification_repo.create_token(
            user_id=user.id,
            token_type="password_reset",
            token_hash=token_hash,
            expires_at=expires_at,
        )

        await self.audit_repo.log_action(
            user_id=user.id,
            action="user.password_reset_requested",
            resource_type="user",
            resource_id=str(user.id),
            ip_address=ip_address,
        )

        await self.db.commit()
        return raw_token

    async def reset_password(self, raw_token: str, new_password: str, ip_address: str | None = None) -> None:
        """Consume password reset token, update password, and invalidate all existing sessions."""
        token_hash = hash_token(raw_token)
        token_record = await self.verification_repo.get_valid_token(token_hash, "password_reset")

        if not token_record:
            raise ValidationError("Invalid, expired, or already used password reset token")

        user = await self.user_repo.get_by_id(token_record.user_id)
        if not user or user.status != "active":
            raise NotFoundError("User not found")

        # Update password
        user.password_hash = hash_password(new_password)
        await self.verification_repo.mark_as_used(token_record.id)

        # Invalidate all active sessions for this user upon password reset
        await self.session_repo.revoke_all_user_sessions(user.id)

        await self.audit_repo.log_action(
            user_id=user.id,
            action="user.password_reset_completed",
            resource_type="user",
            resource_id=str(user.id),
            ip_address=ip_address,
        )

        await self.db.commit()

    async def create_email_verification_token(self, user_id: uuid.UUID) -> str:
        """Create email verification token for user."""
        raw_token = generate_secure_token(32)
        token_hash = hash_token(raw_token)
        expires_at = datetime.now(timezone.utc) + timedelta(days=3)

        await self.verification_repo.create_token(
            user_id=user_id,
            token_type="email_verification",
            token_hash=token_hash,
            expires_at=expires_at,
        )
        await self.db.commit()
        return raw_token

    async def verify_email(self, raw_token: str, ip_address: str | None = None) -> None:
        """Consume email verification token."""
        token_hash = hash_token(raw_token)
        token_record = await self.verification_repo.get_valid_token(token_hash, "email_verification")

        if not token_record:
            raise ValidationError("Invalid or expired email verification token")

        user = await self.user_repo.get_by_id(token_record.user_id)
        if not user:
            raise NotFoundError("User not found")

        user.is_verified = True
        await self.verification_repo.mark_as_used(token_record.id)

        await self.audit_repo.log_action(
            user_id=user.id,
            action="user.email_verified",
            resource_type="user",
            resource_id=str(user.id),
            ip_address=ip_address,
        )

        await self.db.commit()
