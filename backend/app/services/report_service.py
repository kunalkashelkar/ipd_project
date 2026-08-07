# ============================================================
# Report Service
# ============================================================

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import NotFoundError
from backend.app.repositories.report_repository import ReportRepository
from backend.app.repositories.scan_repository import ScanRepository
from backend.app.services.audit_service import AuditService


class ReportService:
    """Business logic for scan reports."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.report_repo = ReportRepository(db)
        self.scan_repo = ScanRepository(db)
        self.audit = AuditService(db)

    async def get_scan_reports(
        self,
        scan_id: uuid.UUID,
        *,
        page: int = 1,
        page_size: int = 20,
    ):
        """Get paginated reports for a scan."""
        scan = await self.scan_repo.get_by_id(scan_id)
        if not scan:
            raise NotFoundError(f"Scan {scan_id} not found")

        return await self.report_repo.get_scan_reports(
            scan_id, page=page, page_size=page_size
        )

    async def request_report(
        self,
        scan_id: uuid.UUID,
        format: str,
        user_id: uuid.UUID,
    ):
        """Manually trigger report generation."""
        scan = await self.scan_repo.get_by_id(scan_id)
        if not scan:
            raise NotFoundError(f"Scan {scan_id} not found")

        report = await self.report_repo.create(
            scan_id=scan_id,
            format=format,
            status="pending",
        )

        await self.audit.log(
            user_id=user_id,
            action="report.requested",
            resource_type="report",
            resource_id=str(report.id),
        )

        # Trigger generation (mocked for MVP)
        from backend.app.workers.report_tasks import generate_report_task
        generate_report_task.delay(str(scan_id))

        return report
