# ============================================================
# Auth Service — Registration, Login, Token Management
# ============================================================

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import AuthenticationError, ConflictError, ValidationError
from backend.app.core.security import (
    create_token_pair,
    decode_token,
    hash_password,
    verify_password,
)
from backend.app.repositories.audit_repository import AuditRepository
from backend.app.repositories.user_repository import UserRepository


class AuthService:
    """Handles authentication business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)
        self.audit_repo = AuditRepository(db)

    async def register(
        self,
        *,
        name: str,
        email: str,
        password: str,
        role: str = "researcher",
        ip_address: str | None = None,
    ) -> dict:
        """Register a new user.

        Returns token pair on success.
        """
        # Check duplicate email
        if await self.user_repo.email_exists(email):
            raise ConflictError("Email is already registered")

        # Validate role
        if role not in ("admin", "researcher", "developer"):
            raise ValidationError("Invalid role")

        # Create user
        user = await self.user_repo.create(
            name=name,
            email=email,
            password_hash=hash_password(password),
            role=role,
            status="active",
        )

        # Audit log
        await self.audit_repo.log_action(
            user_id=user.id,
            action="user.registered",
            resource_type="user",
            resource_id=str(user.id),
            ip_address=ip_address,
        )

        # Generate tokens
        tokens = create_token_pair(str(user.id), user.email, user.role)
        return {
            "user": user,
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
        """Authenticate a user and return tokens.

        Raises AuthenticationError on failure.
        """
        user = await self.user_repo.get_by_email(email)

        if user is None or not verify_password(password, user.password_hash):
            # Log failed attempt (user_id may be None)
            await self.audit_repo.log_action(
                user_id=user.id if user else None,
                action="user.login_failed",
                resource_type="user",
                ip_address=ip_address,
                user_agent=user_agent,
                metadata={"email": email},
            )
            raise AuthenticationError("Invalid email or password")

        if user.status != "active":
            raise AuthenticationError("Account is not active")

        # Update last login
        await self.user_repo.update_last_login(user)

        # Audit log
        await self.audit_repo.log_action(
            user_id=user.id,
            action="user.login",
            resource_type="user",
            resource_id=str(user.id),
            ip_address=ip_address,
            user_agent=user_agent,
        )

        # Generate tokens
        tokens = create_token_pair(str(user.id), user.email, user.role)
        return {
            "user": user,
            "tokens": tokens,
        }

    async def refresh_token(self, refresh_token: str) -> dict:
        """Issue new token pair from a valid refresh token."""
        payload = decode_token(refresh_token)

        if payload.get("type") != "refresh":
            raise AuthenticationError("Invalid token type — expected refresh token")

        user_id = payload.get("sub")
        if user_id is None:
            raise AuthenticationError("Invalid token payload")

        user = await self.user_repo.get_by_id(uuid.UUID(user_id))
        if user is None:
            raise AuthenticationError("User not found")

        if user.status != "active":
            raise AuthenticationError("Account is not active")

        tokens = create_token_pair(str(user.id), user.email, user.role)
        return {
            "user": user,
            "tokens": tokens,
        }

    async def logout(
        self,
        user_id: uuid.UUID,
        ip_address: str | None = None,
    ) -> None:
        """Log the logout event.

        For stateless JWT, actual token invalidation requires a blacklist
        (future enhancement). For now, we just log the event.
        """
        await self.audit_repo.log_action(
            user_id=user_id,
            action="user.logout",
            resource_type="user",
            resource_id=str(user_id),
            ip_address=ip_address,
        )
