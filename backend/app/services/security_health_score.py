# ============================================================
# Security Health Score Service (Phase 7 — Versioned Score Engine)
# ============================================================
# Authoritative implementation of the platform Security Health Score.
# Version: v1.0.0
# Formula:
#   Base Score = 100.0
#   Severity Penalties (Active Findings):
#     - Critical: -15.0 pts
#     - High:     -8.0 pts
#     - Medium:   -3.0 pts
#     - Low:      -1.0 pts
#   Remediation Recovery Bonus:
#     + 10.0 * (Resolved Findings / Total Findings)
#   Clamped strictly to [0.0, 100.0].
# Ratings:
#   A: 90.0 - 100.0
#   B: 80.0 - 89.9
#   C: 70.0 - 79.9
#   D: 60.0 - 69.9
#   F:  0.0 - 59.9
# ============================================================

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.finding import Finding
from backend.app.models.project import Project
from backend.app.models.scan import Scan


class SecurityHealthScoreService:
    """Computes versioned, deterministic Security Health Scores from authoritative finding records."""

    VERSION = "v1.0.0"

    PENALTIES = {
        "critical": 15.0,
        "high": 8.0,
        "medium": 3.0,
        "low": 1.0,
        "info": 0.0,
    }

    def __init__(self, db: AsyncSession):
        self.db = db

    @classmethod
    def get_rating(cls, score: float) -> str:
        """Derive letter grade from score."""
        if score >= 90.0:
            return "A"
        if score >= 80.0:
            return "B"
        if score >= 70.0:
            return "C"
        if score >= 60.0:
            return "D"
        return "F"

    @classmethod
    def compute_score_from_counts(
        cls,
        severity_counts: dict[str, int],
        total_findings: int,
        resolved_findings: int,
    ) -> dict[str, Any]:
        """Pure calculation function for testing and reusability."""
        base = 100.0

        penalty = sum(
            severity_counts.get(sev, 0) * cls.PENALTIES.get(sev, 0.0)
            for sev in cls.PENALTIES
        )

        recovery = 0.0
        if total_findings > 0:
            recovery = 10.0 * (resolved_findings / total_findings)

        final_score = max(0.0, min(100.0, round(base - penalty + recovery, 1)))

        return {
            "score": final_score,
            "rating": cls.get_rating(final_score),
            "status": "CALCULATED",
            "version": cls.VERSION,
            "penalties_applied": penalty,
            "recovery_bonus": round(recovery, 1),
            "formula": "100.0 - sum(active_severity * penalty) + 10.0 * (resolved / total)",
        }

    async def calculate_for_project(self, project_id: uuid.UUID) -> dict[str, Any]:
        """Compute authoritative score for a project, requiring at least one completed scan."""
        # 1. Verify if at least one completed scan exists
        scan_count_stmt = select(func.count(Scan.id)).where(
            Scan.project_id == project_id, Scan.status == "completed"
        )
        completed_scans = (await self.db.execute(scan_count_stmt)).scalar() or 0
        if completed_scans == 0:
            return {
                "score": None,
                "rating": None,
                "status": "NO_DATA",
                "message": "Run your first security scan to establish a security health score.",
                "version": self.VERSION,
                "penalties_applied": 0.0,
                "recovery_bonus": 0.0,
                "formula": "100.0 - sum(active_severity * penalty) + 10.0 * (resolved / total)",
            }

        stmt = (
            select(
                func.lower(Finding.severity),
                func.upper(Finding.status),
                func.count(Finding.id),
            )
            .where(Finding.project_id == project_id)
            .group_by(func.lower(Finding.severity), func.upper(Finding.status))
        )
        res = await self.db.execute(stmt)
        rows = res.all()

        active_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        total_findings = 0
        resolved_findings = 0

        for sev, st, count in rows:
            total_findings += count
            if st in ("FIXED", "VERIFIED"):
                resolved_findings += count
            elif st not in ("FALSE_POSITIVE", "SUPPRESSED", "RISK_ACCEPTED"):
                active_counts[sev] = active_counts.get(sev, 0) + count

        return self.compute_score_from_counts(
            severity_counts=active_counts,
            total_findings=total_findings,
            resolved_findings=resolved_findings,
        )

    async def calculate_for_organization(self, org_id: uuid.UUID) -> dict[str, Any]:
        """Compute authoritative score across an organization, requiring at least one completed scan."""
        # 1. Verify if at least one completed scan exists in the organization
        scan_count_stmt = (
            select(func.count(Scan.id))
            .join(Project, Scan.project_id == Project.id)
            .where(
                Project.organization_id == org_id,
                Project.is_archived.is_(False),
                Scan.status == "completed",
            )
        )
        completed_scans = (await self.db.execute(scan_count_stmt)).scalar() or 0
        if completed_scans == 0:
            return {
                "score": None,
                "rating": None,
                "status": "NO_DATA",
                "message": "Run your first security scan to establish a security health score.",
                "version": self.VERSION,
                "penalties_applied": 0.0,
                "recovery_bonus": 0.0,
                "formula": "100.0 - sum(active_severity * penalty) + 10.0 * (resolved / total)",
            }

        stmt = (
            select(
                func.lower(Finding.severity),
                func.upper(Finding.status),
                func.count(Finding.id),
            )
            .join(Project, Finding.project_id == Project.id)
            .where(Project.organization_id == org_id, Project.is_archived.is_(False))
            .group_by(func.lower(Finding.severity), func.upper(Finding.status))
        )
        res = await self.db.execute(stmt)
        rows = res.all()

        active_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        total_findings = 0
        resolved_findings = 0

        for sev, st, count in rows:
            total_findings += count
            if st in ("FIXED", "VERIFIED"):
                resolved_findings += count
            elif st not in ("FALSE_POSITIVE", "SUPPRESSED", "RISK_ACCEPTED"):
                active_counts[sev] = active_counts.get(sev, 0) + count

        return self.compute_score_from_counts(
            severity_counts=active_counts,
            total_findings=total_findings,
            resolved_findings=resolved_findings,
        )
