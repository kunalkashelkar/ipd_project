# ============================================================
# Analytics Service (Phase 7 — Authoritative Data Aggregation)
# ============================================================

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.core.exceptions import NotFoundError, ValidationError
from backend.app.models.ai_prediction import AIPrediction
from backend.app.models.finding import Finding, FindingOccurrence, FindingStatusHistory
from backend.app.models.project import Project
from backend.app.models.remediation import Remediation, RemediationValidation
from backend.app.models.repository import Repository
from backend.app.models.scan import Scan
from backend.app.services.security_health_score import SecurityHealthScoreService


class AnalyticsService:
    """Provides authoritative, tenant-safe metrics and historical comparisons."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.score_service = SecurityHealthScoreService(db)

    async def get_dashboard_metrics(
        self,
        organization_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
        role: str | None = None,
    ) -> dict[str, Any]:
        """Get concise posture metrics for the main dashboard."""
        project_query = select(Project).where(Project.is_archived.is_(False))
        scan_query = select(Scan).join(Project, Scan.project_id == Project.id)
        finding_query = select(Finding).join(Project, Finding.project_id == Project.id)

        if organization_id is not None:
            project_query = project_query.where(Project.organization_id == organization_id)
            scan_query = scan_query.where(Project.organization_id == organization_id)
            finding_query = finding_query.where(Finding.organization_id == organization_id)
        elif role != "admin" and user_id is not None:
            project_query = project_query.where(Project.owner_id == user_id)
            scan_query = scan_query.where(Project.owner_id == user_id)
            finding_query = finding_query.where(Project.owner_id == user_id)

        total_projects = (await self.db.execute(select(func.count()).select_from(project_query.subquery()))).scalar() or 0
        total_scans = (await self.db.execute(select(func.count()).select_from(scan_query.subquery()))).scalar() or 0
        completed_scans = (await self.db.execute(
            select(func.count()).select_from(scan_query.where(Scan.status == "completed").subquery())
        )).scalar() or 0
        failed_scans = (await self.db.execute(
            select(func.count()).select_from(scan_query.where(Scan.status == "failed").subquery())
        )).scalar() or 0

        # Authoritative Active Finding counts
        finding_filters = [
            func.upper(Finding.status).notin_(["FALSE_POSITIVE", "SUPPRESSED", "RISK_ACCEPTED"])
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

        # Top CWEs
        top_cwe = []
        if total_vulnerabilities > 0:
            cwe_query = (
                select(Finding.cwe_id, func.count(Finding.id.distinct()))
                .join(Project, Finding.project_id == Project.id)
                .where(
                    *finding_filters,
                    Finding.cwe_id.isnot(None),
                    Finding.cwe_id != "",
                    Finding.cwe_id != "N/A",
                )
                .group_by(Finding.cwe_id)
                .order_by(func.count(Finding.id.distinct()).desc())
                .limit(5)
            )
            cwe_result = await self.db.execute(cwe_query)
            top_cwe = [{"cwe_id": row[0], "count": row[1]} for row in cwe_result.all()]

        # Health Score
        if organization_id is not None:
            health_data = await self.score_service.calculate_for_organization(organization_id)
        else:
            health_data = {"score": 100.0, "rating": "A", "version": "v1.0.0"}

        # Recent scans
        recent_scans_stmt = (
            select(Scan)
            .join(Project, Scan.project_id == Project.id)
            .where(*([Project.organization_id == organization_id] if organization_id else []))
            .order_by(Scan.created_at.desc())
            .limit(5)
        )
        recent_res = await self.db.execute(recent_scans_stmt)
        recent_scans = [
            {
                "id": str(s.id),
                "public_id": s.public_id,
                "status": s.status,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in recent_res.scalars().all()
        ]

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
            "recent_scans": recent_scans,
            "scan_success_rate": (completed_scans / total_scans) if total_scans > 0 else 0.0,
            "vulnerabilities_by_cwe": top_cwe,
            "health_score": health_data.get("score"),
            "health_rating": health_data.get("rating"),
            "health_status": health_data.get("status", "SCORED"),
            "score_version": health_data.get("version", "v1.0.0"),
        }

    async def get_analytics_metrics(
        self,
        organization_id: uuid.UUID,
        project_id: uuid.UUID | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
    ) -> dict[str, Any]:
        """Deep authoritative analytics metrics."""
        filters = [Finding.organization_id == organization_id]
        if project_id:
            filters.append(Finding.project_id == project_id)

        # 1. Base Finding counts
        base_stmt = select(Finding).where(*filters)
        findings_res = await self.db.execute(base_stmt)
        all_findings = findings_res.scalars().all()

        total_findings = len(all_findings)
        active_findings = 0
        resolved_findings = 0
        new_findings = 0
        false_positive_count = 0
        critical_count = 0
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        cwe_counts: dict[str, int] = {}
        resolved_durations: list[float] = []

        now = datetime.now(timezone.utc)
        window_start = from_date or (now - timedelta(days=30))

        for f in all_findings:
            st = f.status.upper()
            sev = f.severity.lower()

            if st in ("FALSE_POSITIVE", "SUPPRESSED"):
                false_positive_count += 1
            elif st in ("FIXED", "VERIFIED"):
                resolved_findings += 1
                if f.fixed_at and f.first_seen_at:
                    dur_hours = (f.fixed_at - f.first_seen_at).total_seconds() / 3600.0
                    if dur_hours >= 0:
                        resolved_durations.append(dur_hours)
            else:
                active_findings += 1
                severity_counts[sev] = severity_counts.get(sev, 0) + 1
                if sev == "critical":
                    critical_count += 1
                cwe = f.cwe_id
                if cwe and cwe != "N/A":
                    cwe_counts[cwe] = cwe_counts.get(cwe, 0) + 1

            if f.first_seen_at and f.first_seen_at >= window_start:
                new_findings += 1

        top_cwes = sorted(
            [{"cwe_id": k, "count": v} for k, v in cwe_counts.items()],
            key=lambda x: x["count"],
            reverse=True,
        )[:8]

        # 2. MTTR
        mttr_hours = round(sum(resolved_durations) / len(resolved_durations), 1) if resolved_durations else None

        # 3. Health score
        if project_id:
            health_score_data = await self.score_service.calculate_for_project(project_id)
        else:
            health_score_data = await self.score_service.calculate_for_organization(organization_id)

        # 4. Finding & Risk Trends (daily buckets over last 14 days)
        trend_days = 14
        trend_start = now - timedelta(days=trend_days)
        daily_trends = []
        risk_trends = []

        for day_offset in range(trend_days + 1):
            day_target = (trend_start + timedelta(days=day_offset)).date()
            day_iso = day_target.isoformat()

            # Count findings first seen on or before this day and not fixed before this day
            active_on_day = sum(
                1 for f in all_findings
                if f.first_seen_at and f.first_seen_at.date() <= day_target
                and (not f.fixed_at or f.fixed_at.date() > day_target)
                and f.status.upper() not in ("FALSE_POSITIVE", "SUPPRESSED")
            )
            new_on_day = sum(
                1 for f in all_findings
                if f.first_seen_at and f.first_seen_at.date() == day_target
            )
            resolved_on_day = sum(
                1 for f in all_findings
                if f.fixed_at and f.fixed_at.date() == day_target
            )

            daily_trends.append({
                "date": day_iso,
                "active": active_on_day,
                "new": new_on_day,
                "resolved": resolved_on_day,
            })

            # Calculate average risk on this day
            risks_on_day = [
                f.risk_score for f in all_findings
                if f.first_seen_at and f.first_seen_at.date() <= day_target
                and (not f.fixed_at or f.fixed_at.date() > day_target)
            ]
            avg_risk = round(sum(risks_on_day) / len(risks_on_day), 1) if risks_on_day else 0.0
            risk_trends.append({
                "date": day_iso,
                "average_risk": avg_risk,
            })

        # 5. Repository stats
        repo_stmt = (
            select(Repository)
            .join(Project, Repository.project_id == Project.id)
            .where(Project.organization_id == organization_id)
        )
        if project_id:
            repo_stmt = repo_stmt.where(Repository.project_id == project_id)
        repos_res = await self.db.execute(repo_stmt)
        repos = repos_res.scalars().all()

        repo_stats = [
            {
                "id": str(r.id),
                "url": r.repository_url,
                "provider": r.provider,
                "branch": r.branch,
                "status": r.status,
            }
            for r in repos
        ]

        # 6. Authoritative AI Metrics
        rem_stmt = (
            select(Remediation)
            .join(Finding, Remediation.finding_id == Finding.id)
            .where(Finding.organization_id == organization_id)
        )
        if project_id:
            rem_stmt = rem_stmt.where(Finding.project_id == project_id)
        rem_res = await self.db.execute(rem_stmt)
        remediations = rem_res.scalars().all()

        ai_metrics = {
            "total_remediations_generated": len(remediations),
            "remediation_acceptance_rate": 0.0,
            "validation_pass_rate": 0.0,
            "has_authoritative_data": len(remediations) > 0,
        }
        if remediations:
            accepted = sum(1 for r in remediations if str(r.status).lower() in ("accepted", "applied", "verified"))
            ai_metrics["remediation_acceptance_rate"] = round(accepted / len(remediations), 2)

        return {
            "health_score": health_score_data,
            "active_findings": active_findings,
            "total_findings": total_findings,
            "new_findings": new_findings,
            "resolved_findings": resolved_findings,
            "critical_findings": critical_count,
            "severity_breakdown": severity_counts,
            "cwe_distribution": top_cwes,
            "finding_trends": daily_trends,
            "risk_trends": risk_trends,
            "mttr_hours": mttr_hours,
            "remediation_rate": round(resolved_findings / total_findings, 2) if total_findings > 0 else 0.0,
            "false_positive_rate": round(false_positive_count / total_findings, 2) if total_findings > 0 else 0.0,
            "ai_metrics": ai_metrics,
            "repository_stats": repo_stats,
        }

    async def compare_scans(
        self,
        baseline_scan_id: str | uuid.UUID,
        current_scan_id: str | uuid.UUID,
        org_id: uuid.UUID,
        project_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """Perform authoritative scan-to-scan finding comparison using Finding.fingerprint."""
        from backend.app.core.identifiers import is_valid_uuid
        from backend.app.core.exceptions import BadRequestError
        from sqlalchemy import or_

        sid_a_str = str(baseline_scan_id).strip()
        cond_a = or_(Scan.id == uuid.UUID(sid_a_str), Scan.public_id == sid_a_str) if is_valid_uuid(sid_a_str) else (Scan.public_id == sid_a_str)

        sid_b_str = str(current_scan_id).strip()
        cond_b = or_(Scan.id == uuid.UUID(sid_b_str), Scan.public_id == sid_b_str) if is_valid_uuid(sid_b_str) else (Scan.public_id == sid_b_str)

        scan_a_stmt = select(Scan).join(Project).where(cond_a, Project.organization_id == org_id)
        scan_b_stmt = select(Scan).join(Project).where(cond_b, Project.organization_id == org_id)

        scan_a = (await self.db.execute(scan_a_stmt)).scalar_one_or_none()
        scan_b = (await self.db.execute(scan_b_stmt)).scalar_one_or_none()

        if not scan_a:
            raise NotFoundError(f"Baseline scan '{baseline_scan_id}' not found in active organization")
        if not scan_b:
            raise NotFoundError(f"Current scan '{current_scan_id}' not found in active organization")

        if project_id and (scan_a.project_id != project_id or scan_b.project_id != project_id):
            raise BadRequestError("The selected scans must belong to the same project.")

        if scan_a.project_id != scan_b.project_id:
            raise BadRequestError("The selected scans belong to different projects.")

        if scan_a.status != "completed" or scan_b.status != "completed":
            raise BadRequestError("Both scans must be in completed status for comparison.")

        # Query occurrences and persistent findings for both scans
        occ_a_stmt = (
            select(FindingOccurrence)
            .options(selectinload(FindingOccurrence.finding))
            .where(FindingOccurrence.scan_id == scan_a.id)
        )
        occ_b_stmt = (
            select(FindingOccurrence)
            .options(selectinload(FindingOccurrence.finding))
            .where(FindingOccurrence.scan_id == scan_b.id)
        )

        occs_a = (await self.db.execute(occ_a_stmt)).scalars().all()
        occs_b = (await self.db.execute(occ_b_stmt)).scalars().all()

        findings_a_by_fp = {occ.finding.fingerprint: occ.finding for occ in occs_a if occ.finding}
        findings_b_by_fp = {occ.finding.fingerprint: occ.finding for occ in occs_b if occ.finding}

        fps_a = set(findings_a_by_fp.keys())
        fps_b = set(findings_b_by_fp.keys())

        existing_fps = fps_a.intersection(fps_b)
        new_fps = fps_b - fps_a
        fixed_fps = fps_a - fps_b

        # Check for reopened findings (in new_fps but finding was first_seen prior to scan_b)
        reopened_fps = set()
        for fp in new_fps:
            f = findings_b_by_fp[fp]
            if f.first_seen_at and scan_a.created_at and f.first_seen_at < scan_a.created_at:
                reopened_fps.add(fp)

        def _serialize_finding(f: Finding) -> dict[str, Any]:
            return {
                "id": str(f.id),
                "public_id": f.public_id,
                "title": f.title,
                "severity": f.severity,
                "cwe_id": f.cwe_id,
                "status": f.status,
                "risk_score": f.risk_score,
                "fingerprint": f.fingerprint,
            }

        return {
            "baseline_scan_id": scan_a.public_id,
            "current_scan_id": scan_b.public_id,
            "existing_count": len(existing_fps),
            "new_count": len(new_fps),
            "fixed_count": len(fixed_fps),
            "reopened_count": len(reopened_fps),
            "existing_findings": [_serialize_finding(findings_b_by_fp[fp]) for fp in existing_fps],
            "new_findings": [_serialize_finding(findings_b_by_fp[fp]) for fp in new_fps],
            "fixed_findings": [_serialize_finding(findings_a_by_fp[fp]) for fp in fixed_fps],
            "reopened_findings": [_serialize_finding(findings_b_by_fp[fp]) for fp in reopened_fps],
        }
