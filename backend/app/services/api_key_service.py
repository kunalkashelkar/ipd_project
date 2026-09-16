# ============================================================
# Phase 2 API Key Service
# ============================================================

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import NotFoundError
from backend.app.core.security import generate_api_key
from backend.app.models.api_key import ApiKey
from backend.app.repositories.audit_repository import AuditRepository
from backend.app.repositories.phase2_repositories import ApiKeyRepository


class ApiKeyService:
    """Business logic for organization-scoped API key management."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.key_repo = ApiKeyRepository(db)
        self.audit_repo = AuditRepository(db)

    async def create_key(
        self,
        *,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
        name: str,
        expires_in_days: int | None = None,
        ip_address: str | None = None,
    ) -> tuple[ApiKey, str]:
        """Create an API key returning the ApiKey model and the plaintext secret key (shown ONCE)."""
        full_secret, prefix, key_hash = generate_api_key()

        expires_at = None
        if expires_in_days:
            expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)

        api_key = await self.key_repo.create_api_key(
            org_id=org_id,
            user_id=user_id,
            name=name,
            key_prefix=prefix,
            key_hash=key_hash,
            expires_at=expires_at,
        )

        await self.audit_repo.log_action(
            user_id=user_id,
            organization_id=org_id,
            action="api_key.created",
            resource_type="api_key",
            resource_id=str(api_key.id),
            ip_address=ip_address,
            metadata={"name": name, "key_prefix": prefix},
        )

        await self.db.commit()
        return api_key, full_secret

    async def list_keys(self, org_id: uuid.UUID) -> Sequence[ApiKey]:
        """List metadata for API keys in the organization (never returns plaintext secrets)."""
        return await self.key_repo.list_for_org(org_id)

    async def revoke_key(
        self,
        *,
        key_id: uuid.UUID,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
        ip_address: str | None = None,
    ) -> None:
        """Revoke an active API key."""
        api_key = await self.key_repo.get_by_id(key_id, org_id)
        if not api_key:
            raise NotFoundError("API key not found in organization")

        await self.key_repo.revoke_api_key(key_id, org_id)

        await self.audit_repo.log_action(
            user_id=user_id,
            organization_id=org_id,
            action="api_key.revoked",
            resource_type="api_key",
            resource_id=str(key_id),
            ip_address=ip_address,
        )

        await self.db.commit()
