# ============================================================
# Phase 2 Audit Log Router
# ============================================================

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.authorization import require_permission
from backend.app.core.response import success_response
from backend.app.database.session import get_db
from backend.app.models.audit_log import AuditLog
from backend.app.models.organization import Organization, OrganizationMember

router = APIRouter(prefix="/organizations/{organization_id}/audit", tags=["Audit Logs"])


@router.get("", summary="List audit events for the organization")
async def list_audit_logs(
    organization_id: uuid.UUID,
    org_context: tuple[Organization, OrganizationMember] = Depends(require_permission("audit.read")),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve immutable audit history strictly scoped to the organization."""
    stmt = (
        select(AuditLog)
        .where(AuditLog.organization_id == organization_id)
        .order_by(AuditLog.created_at.desc())
        .limit(100)
    )
    result = await db.execute(stmt)
    logs = result.scalars().all()

    data = [
        {
            "id": str(log.id),
            "user_id": str(log.user_id) if log.user_id else None,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "ip_address": log.ip_address,
            "metadata": log.metadata_json,
            "created_at": log.created_at.isoformat(),
        }
        for log in logs
    ]

    return success_response(data=data, message="Audit logs retrieved")
