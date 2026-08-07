# ============================================================
# Result Service
# ============================================================

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import AuthorizationError, NotFoundError
from backend.app.repositories.result_repository import ResultRepository
from backend.app.repositories.scan_repository import ScanRepository
from backend.app.services.audit_service import AuditService


class ResultService:
    """Business logic for scan results and findings."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.result_repo = ResultRepository(db)
        self.scan_repo = ScanRepository(db)
        self.audit = AuditService(db)

    async def get_scan_results(
        self,
        scan_id: uuid.UUID,
        user_id: uuid.UUID,
        role: str,
        *,
        page: int = 1,
        page_size: int = 20,
        severity: str | None = None,
    ):
        """Get paginated results for a scan."""
        # 1. Verify scan access via project
        scan = await self.scan_repo.get_by_id(scan_id)
        if not scan:
            raise NotFoundError(f"Scan {scan_id} not found")

        # In a real app, you'd check project access here
        # For simplicity, we assume the router handles the access check
        # using the require_project_access dependency.

        return await self.result_repo.get_scan_results(
            scan_id, page=page, page_size=page_size, severity=severity
        )

    async def get_scan_summary(self, scan_id: uuid.UUID):
        """Get aggregated vulnerability summary."""
        scan = await self.scan_repo.get_by_id(scan_id)
        if not scan:
            raise NotFoundError(f"Scan {scan_id} not found")

        return await self.result_repo.get_summary(scan_id)

    async def submit_feedback(
        self,
        result_id: uuid.UUID,
        user_id: uuid.UUID,
        is_correct: bool,
        comment: str | None = None,
    ):
        """Submit user feedback for an AI prediction."""
        result = await self.result_repo.get_by_id(result_id)
        if not result:
            raise NotFoundError("Result not found")

        # Create feedback record
        from backend.app.models.feedback import Feedback
        feedback = Feedback(
            scan_result_id=result_id,
            user_id=user_id,
            is_correct=is_correct,
            comment=comment,
        )
        self.db.add(feedback)
        await self.db.commit()

        await self.audit.log(
            user_id=user_id,
            action="feedback.submitted",
            resource_type="scan_result",
            resource_id=str(result_id),
        )

        return feedback
