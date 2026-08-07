# ============================================================
# Analytics Service
# ============================================================

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.project import Project
from backend.app.models.scan import Scan
from backend.app.models.scan_result import ScanResult


class AnalyticsService:
    """Provides dashboard analytics data."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_dashboard_metrics(self, user_id: uuid.UUID, role: str) -> dict:
        """Get high-level metrics for the dashboard."""
        
        # Base queries (filtered by user if not admin)
        project_query = select(Project).where(Project.is_archived == False)  # noqa: E712
        scan_query = select(Scan)
        result_query = select(ScanResult).join(Scan)

        if role != "admin":
            project_query = project_query.where(Project.owner_id == user_id)
            scan_query = scan_query.join(Project).where(Project.owner_id == user_id)
            result_query = result_query.where(Project.owner_id == user_id)

        # Total projects
        total_projects = (await self.db.execute(select(func.count()).select_from(project_query.subquery()))).scalar() or 0

        # Scan metrics
        total_scans = (await self.db.execute(select(func.count()).select_from(scan_query.subquery()))).scalar() or 0
        
        completed_scans = (await self.db.execute(
            select(func.count()).select_from(scan_query.where(Scan.status == "completed").subquery())
        )).scalar() or 0
        
        failed_scans = (await self.db.execute(
            select(func.count()).select_from(scan_query.where(Scan.status == "failed").subquery())
        )).scalar() or 0

        # Vulnerability counts by severity
        severity_counts = {}
        if total_scans > 0:
            severity_query = select(ScanResult.severity, func.count()).select_from(result_query.subquery()).group_by(ScanResult.severity)
            severity_result = await self.db.execute(severity_query)
            severity_counts = {row[0]: row[1] for row in severity_result.all()}

        total_vulnerabilities = sum(severity_counts.values())

        # Top CWEs
        top_cwe = []
        if total_vulnerabilities > 0:
            cwe_query = (
                select(ScanResult.cwe_id, func.count())
                .select_from(result_query.subquery())
                .where(ScanResult.cwe_id.isnot(None))
                .group_by(ScanResult.cwe_id)
                .order_by(func.count().desc())
                .limit(5)
            )
            cwe_result = await self.db.execute(cwe_query)
            top_cwe = [{"cwe_id": row[0], "count": row[1]} for row in cwe_result.all()]

        return {
            "total_projects": total_projects,
            "total_scans": total_scans,
            "completed_scans": completed_scans,
            "failed_scans": failed_scans,
            "total_vulnerabilities": total_vulnerabilities,
            "severity_breakdown": {
                "critical": severity_counts.get("critical", 0),
                "high": severity_counts.get("high", 0),
                "medium": severity_counts.get("medium", 0),
                "low": severity_counts.get("low", 0),
                "info": severity_counts.get("info", 0),
            },
            "recent_scans": [],  # Could add recent scans here
            "scan_success_rate": (completed_scans / total_scans) if total_scans > 0 else 0.0,
            "vulnerabilities_by_cwe": top_cwe,
        }
