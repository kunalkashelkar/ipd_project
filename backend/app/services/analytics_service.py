# ============================================================
# Analytics Service
# ============================================================

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.finding import Finding
from backend.app.models.project import Project
from backend.app.models.scan import Scan


class AnalyticsService:
    """Provides dashboard analytics data using authoritative Phase 5 Finding domain."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_dashboard_metrics(
        self,
        organization_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
        role: str | None = None,
    ) -> dict:
        """Get high-level metrics for the dashboard strictly scoped to an organization.
        
        Definitions:
        - Total Projects: Active, non-archived projects in organization.
        - Total Scans: Scans executed across projects in organization.
        - Total Findings: Persistent deduplicated findings in organization (excluding false positives/suppressed).
        - Critical Issues: Active critical findings requiring immediate triage.
        """
        # 1. Base queries scoped to tenant organization
        project_query = select(Project).where(Project.is_archived == False)  # noqa: E712
        scan_query = select(Scan).join(Project, Scan.project_id == Project.id)
        
        # Authoritative Phase 5 Finding query
        finding_query = select(Finding).join(Project, Finding.project_id == Project.id)

        if organization_id is not None:
            project_query = project_query.where(Project.organization_id == organization_id)
            scan_query = scan_query.where(Project.organization_id == organization_id)
            finding_query = finding_query.where(Finding.organization_id == organization_id)
        elif role != "admin" and user_id is not None:
            project_query = project_query.where(Project.owner_id == user_id)
            scan_query = scan_query.where(Project.owner_id == user_id)
            finding_query = finding_query.where(Project.owner_id == user_id)

        # 2. Total projects
        total_projects = (await self.db.execute(select(func.count()).select_from(project_query.subquery()))).scalar() or 0

        # 3. Scan metrics
        total_scans = (await self.db.execute(select(func.count()).select_from(scan_query.subquery()))).scalar() or 0
        
        completed_scans = (await self.db.execute(
            select(func.count()).select_from(scan_query.where(Scan.status == "completed").subquery())
        )).scalar() or 0
        
        failed_scans = (await self.db.execute(
            select(func.count()).select_from(scan_query.where(Scan.status == "failed").subquery())
        )).scalar() or 0

        # 4. Authoritative Vulnerability counts from Finding domain
        # Active/unresolved findings (exclude FALSE_POSITIVE and SUPPRESSED from active security counts)
        finding_filters = [
            func.upper(Finding.status).notin_(["FALSE_POSITIVE", "SUPPRESSED"])
        ]
        if organization_id is not None:
            finding_filters.append(Finding.organization_id == organization_id)
        elif role != "admin" and user_id is not None:
            finding_filters.append(Project.owner_id == user_id)

        severity_query = (
            select(
                func.lower(Finding.severity),
                func.count(Finding.id.distinct())
            )
            .join(Project, Finding.project_id == Project.id)
            .where(*finding_filters)
            .group_by(func.lower(Finding.severity))
        )
        severity_result = await self.db.execute(severity_query)
        severity_counts = {row[0]: row[1] for row in severity_result.all()}

        total_vulnerabilities = sum(severity_counts.values())

        # Top CWEs from authoritative findings
        top_cwe = []
        if total_vulnerabilities > 0:
            cwe_query = (
                select(Finding.cwe_id, func.count(Finding.id.distinct()))
                .join(Project, Finding.project_id == Project.id)
                .where(
                    *finding_filters,
                    Finding.cwe_id.isnot(None),
                    Finding.cwe_id != "",
                )
                .group_by(Finding.cwe_id)
                .order_by(func.count(Finding.id.distinct()).desc())
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
            "recent_scans": [],
            "scan_success_rate": (completed_scans / total_scans) if total_scans > 0 else 0.0,
            "vulnerabilities_by_cwe": top_cwe,
        }
