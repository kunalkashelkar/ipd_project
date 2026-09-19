# ============================================================
# Report Repository (Phase 7)
# ============================================================

from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.models.report import Report, ReportFile
from backend.app.repositories.base import BaseRepository


class ReportRepository(BaseRepository[Report]):
    """Repository for Report and ReportFile model operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, Report)

    async def get_by_id_or_public_id(
        self, id_or_pid: str | uuid.UUID
    ) -> Report | None:
        """Find report by internal UUID or public ID."""
        stmt = (
            select(Report)
            .options(
                selectinload(Report.files),
                selectinload(Report.project),
                selectinload(Report.scan),
            )
        )
        try:
            val_uuid = uuid.UUID(str(id_or_pid))
            stmt = stmt.where((Report.id == val_uuid) | (Report.public_id == str(id_or_pid)))
        except ValueError:
            stmt = stmt.where(Report.public_id == str(id_or_pid))

        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_scan_reports(
        self,
        scan_id: uuid.UUID,
        *,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[Sequence[Report], int]:
        """Get reports for a scan."""
        return await self.get_all(
            page=page,
            page_size=page_size,
            filters=[Report.scan_id == scan_id],
            order_by=Report.created_at.desc(),
        )

    async def get_org_reports(
        self,
        org_id: uuid.UUID,
        *,
        project_id: uuid.UUID | None = None,
        scan_id: uuid.UUID | None = None,
        report_type: str | None = None,
        format: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[Sequence[Report], int]:
        """Get paginated reports for an organization with optional filters."""
        filters = [Report.organization_id == org_id]
        if project_id:
            filters.append(Report.project_id == project_id)
        if scan_id:
            filters.append(Report.scan_id == scan_id)
        if report_type:
            filters.append(Report.report_type == report_type)
        if format:
            filters.append(Report.format == format)
        if status:
            filters.append(Report.status == status)

        return await self.get_all(
            page=page,
            page_size=page_size,
            filters=filters,
            order_by=Report.created_at.desc(),
        )

    async def update_status(
        self, report_id: uuid.UUID, status: str, **kwargs
    ) -> Report | None:
        """Update report status."""
        return await self.update(report_id, status=status, **kwargs)
