# ============================================================
# Audit Repository
# ============================================================

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.audit_log import AuditLog
from backend.app.repositories.base import BaseRepository


class AuditRepository(BaseRepository[AuditLog]):
    """Repository for AuditLog model operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, AuditLog)

    async def log_action(
        self,
        *,
        user_id: uuid.UUID | None = None,
        organization_id: uuid.UUID | None = None,
        action: str,
        resource_type: str | None = None,
        resource_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        metadata: dict | None = None,
    ) -> AuditLog:
        """Create an audit log entry."""
        return await self.create(
            user_id=user_id,
            organization_id=organization_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata_json=metadata,
        )


    async def get_user_logs(
        self,
        user_id: uuid.UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        action: str | None = None,
    ) -> tuple[list[AuditLog], int]:
        """Get audit logs for a user."""
        filters = [AuditLog.user_id == user_id]
        if action:
            filters.append(AuditLog.action == action)
        return await self.get_all(
            page=page,
            page_size=page_size,
            filters=filters,
            order_by=AuditLog.created_at.desc(),
        )
