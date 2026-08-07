# ============================================================
# Audit Service
# ============================================================

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.repositories.audit_repository import AuditRepository


class AuditService:
    """Service for creating audit log entries."""

    def __init__(self, db: AsyncSession):
        self.repo = AuditRepository(db)

    async def log(
        self,
        *,
        user_id: uuid.UUID | None = None,
        action: str,
        resource_type: str | None = None,
        resource_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        """Log an action to the audit trail."""
        await self.repo.log_action(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=metadata,
        )
