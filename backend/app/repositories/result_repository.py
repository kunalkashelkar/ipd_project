# ============================================================
# Result Repository
# ============================================================

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.scan_result import ScanResult
from backend.app.repositories.base import BaseRepository


class ResultRepository(BaseRepository[ScanResult]):
    """Repository for ScanResult model operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, ScanResult)

    async def get_scan_results(
        self,
        scan_id: uuid.UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        severity: str | None = None,
    ) -> tuple[list[ScanResult], int]:
        """Get results for a scan with optional severity filter."""
        filters = [ScanResult.scan_id == scan_id]
        if severity:
            filters.append(ScanResult.severity == severity)

        return await self.get_all(
            page=page,
            page_size=page_size,
            filters=filters,
            order_by=ScanResult.created_at.desc(),
        )

    async def get_summary(self, scan_id: uuid.UUID) -> dict:
        """Get aggregated summary for a scan's results."""
        # Total count
        total_result = await self.db.execute(
            select(func.count()).select_from(ScanResult).where(ScanResult.scan_id == scan_id)
        )
        total = total_result.scalar() or 0

        # Severity breakdown
        severity_query = (
            select(ScanResult.severity, func.count())
            .where(ScanResult.scan_id == scan_id)
            .group_by(ScanResult.severity)
        )
        severity_result = await self.db.execute(severity_query)
        severity_counts = {row[0]: row[1] for row in severity_result.all()}

        # Average confidence
        avg_result = await self.db.execute(
            select(func.avg(ScanResult.confidence)).where(ScanResult.scan_id == scan_id)
        )
        avg_confidence = avg_result.scalar() or 0.0

        # Top CWEs
        cwe_query = (
            select(ScanResult.cwe_id, func.count())
            .where(ScanResult.scan_id == scan_id)
            .where(ScanResult.cwe_id.isnot(None))
            .group_by(ScanResult.cwe_id)
            .order_by(func.count().desc())
            .limit(10)
        )
        cwe_result = await self.db.execute(cwe_query)
        top_cwe = [{"cwe_id": row[0], "count": row[1]} for row in cwe_result.all()]

        return {
            "scan_id": str(scan_id),
            "total_vulnerabilities": total,
            "critical": severity_counts.get("critical", 0),
            "high": severity_counts.get("high", 0),
            "medium": severity_counts.get("medium", 0),
            "low": severity_counts.get("low", 0),
            "info": severity_counts.get("info", 0),
            "average_confidence": round(float(avg_confidence), 4),
            "top_cwe": top_cwe,
        }

    async def bulk_create(self, results: list[dict]) -> list[ScanResult]:
        """Insert multiple scan results in bulk."""
        instances = [ScanResult(**r) for r in results]
        self.db.add_all(instances)
        await self.db.flush()
        return instances
