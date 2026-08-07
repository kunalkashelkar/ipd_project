# ============================================================
# Report Repository
# ============================================================

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.report import Report
from backend.app.repositories.base import BaseRepository


class ReportRepository(BaseRepository[Report]):
    """Repository for Report model operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, Report)

    async def get_scan_reports(
        self,
        scan_id: uuid.UUID,
        *,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Report], int]:
        """Get reports for a scan."""
        return await self.get_all(
            page=page,
            page_size=page_size,
            filters=[Report.scan_id == scan_id],
            order_by=Report.created_at.desc(),
        )

    async def update_status(
        self, report_id: uuid.UUID, status: str, **kwargs
    ) -> Report | None:
        """Update report status."""
        return await self.update(report_id, status=status, **kwargs)
