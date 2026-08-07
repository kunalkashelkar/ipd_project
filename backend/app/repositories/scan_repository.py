# ============================================================
# Scan Repository
# ============================================================

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.scan import Scan
from backend.app.repositories.base import BaseRepository


class ScanRepository(BaseRepository[Scan]):
    """Repository for Scan model operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, Scan)

    async def get_project_scans(
        self,
        project_id: uuid.UUID,
        *,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Scan], int]:
        """Get scans for a project."""
        return await self.get_all(
            page=page,
            page_size=page_size,
            filters=[Scan.project_id == project_id],
            order_by=Scan.created_at.desc(),
        )

    async def has_active_scan(self, project_id: uuid.UUID) -> bool:
        """Check if a project has an active (non-terminal) scan."""
        active_statuses = ["pending", "queued", "preprocessing", "ai_running", "storing_results", "generating_report"]
        result = await self.db.execute(
            select(Scan)
            .where(Scan.project_id == project_id)
            .where(Scan.status.in_(active_statuses))
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def update_status(
        self,
        scan_id: uuid.UUID,
        status: str,
        *,
        progress: float | None = None,
        current_stage: str | None = None,
        error_message: str | None = None,
    ) -> Scan | None:
        """Update scan status and progress."""
        kwargs = {"status": status}
        if progress is not None:
            kwargs["progress"] = progress
        if current_stage is not None:
            kwargs["current_stage"] = current_stage
        if error_message is not None:
            kwargs["error_message"] = error_message

        # Set timestamps
        from datetime import datetime, timezone

        if status == "queued":
            kwargs["started_at"] = datetime.now(timezone.utc)
        elif status in ("completed", "failed", "cancelled"):
            kwargs["completed_at"] = datetime.now(timezone.utc)

        return await self.update(scan_id, **kwargs)
