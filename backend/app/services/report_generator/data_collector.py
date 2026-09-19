# ============================================================
# Report Data Collector (Phase 7)
# ============================================================

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.models.finding import Finding, FindingOccurrence
from backend.app.models.organization import Organization
from backend.app.models.project import Project
from backend.app.models.remediation import Remediation, RemediationValidation
from backend.app.models.scan import Scan
from backend.app.models.source_snapshot import SourceSnapshot
from backend.app.services.security_health_score import SecurityHealthScoreService


class ReportDataCollector:
    """Collects authoritative, tenant-safe data for report generation."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.health_score_service = SecurityHealthScoreService(db)

    async def collect(self, scan_id: uuid.UUID) -> dict[str, Any]:
        """Gather scan, project, snapshot, findings, occurrences, remediations, and score."""
        # 1. Load scan with project, snapshot, and organization
        scan_stmt = (
            select(Scan)
            .options(
                selectinload(Scan.project).selectinload(Project.organization),
                selectinload(Scan.source_snapshot),
            )
            .where(Scan.id == scan_id)
        )
        scan_res = await self.db.execute(scan_stmt)
        scan = scan_res.scalar_one_or_none()
        if not scan:
            raise ValueError(f"Scan {scan_id} not found")

        project = scan.project
        org = project.organization if project else None
        snapshot = scan.source_snapshot

        # 2. Query all occurrences for this scan, eagerly loading their persistent Finding
        occ_stmt = (
            select(FindingOccurrence)
            .options(selectinload(FindingOccurrence.finding))
            .where(FindingOccurrence.scan_id == scan_id)
            .order_by(FindingOccurrence.file_path, FindingOccurrence.start_line)
        )
        occ_res = await self.db.execute(occ_stmt)
        occurrences = occ_res.scalars().all()

        # Group occurrences by persistent finding ID
        finding_map: dict[uuid.UUID, dict[str, Any]] = {}
        for occ in occurrences:
            f = occ.finding
            if not f:
                continue
            if f.id not in finding_map:
                finding_map[f.id] = {
                    "id": str(f.id),
                    "public_id": f.public_id,
                    "title": f.title,
                    "vulnerability_type": f.vulnerability_type,
                    "cwe_id": f.cwe_id or "N/A",
                    "severity": f.severity.lower(),
                    "cvss_score": f.cvss_score,
                    "confidence": f.confidence,
                    "risk_score": f.risk_score,
                    "status": f.status,
                    "first_seen_at": f.first_seen_at.isoformat() if f.first_seen_at else None,
                    "last_seen_at": f.last_seen_at.isoformat() if f.last_seen_at else None,
                    "fixed_at": f.fixed_at.isoformat() if f.fixed_at else None,
                    "occurrences": [],
                    "remediations": [],
                }
            finding_map[f.id]["occurrences"].append({
                "id": str(occ.id),
                "file_path": occ.file_path,
                "start_line": occ.start_line,
                "end_line": occ.end_line,
                "function_name": occ.function_name,
                "confidence": occ.confidence,
                "static_evidence": occ.static_evidence_ref,
                "taint_evidence": occ.taint_evidence_ref,
                "graph_evidence": occ.graph_evidence_ref,
                "ai_prediction_id": str(occ.ai_prediction_id) if occ.ai_prediction_id else None,
            })

        finding_ids = list(finding_map.keys())

        # 3. Load remediations and validations for these findings
        if finding_ids:
            rem_stmt = (
                select(Remediation)
                .options(selectinload(Remediation.validations))
                .where(Remediation.finding_id.in_(finding_ids))
                .order_by(Remediation.created_at.desc())
            )
            rem_res = await self.db.execute(rem_stmt)
            for rem in rem_res.scalars().all():
                val_status = "unvalidated"
                if rem.validations:
                    latest_val = rem.validations[0]
                    val_status = latest_val.status.value if hasattr(latest_val.status, "value") else str(latest_val.status)

                if rem.finding_id in finding_map:
                    finding_map[rem.finding_id]["remediations"].append({
                        "id": str(rem.id),
                        "explanation": rem.explanation,
                        "suggested_patch": rem.suggested_patch,
                        "confidence_score": rem.confidence_score,
                        "status": rem.status.value if hasattr(rem.status, "value") else str(rem.status),
                        "validation_status": val_status,
                        "created_at": rem.created_at.isoformat() if rem.created_at else None,
                    })

        findings_list = list(finding_map.values())

        # 4. Aggregate metrics
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        status_counts: dict[str, int] = {}
        cwe_counts: dict[str, int] = {}

        for f in findings_list:
            sev = f["severity"]
            severity_counts[sev] = severity_counts.get(sev, 0) + 1
            st = f["status"].upper()
            status_counts[st] = status_counts.get(st, 0) + 1
            cwe = f["cwe_id"]
            if cwe and cwe != "N/A":
                cwe_counts[cwe] = cwe_counts.get(cwe, 0) + 1

        top_cwes = sorted(
            [{"cwe_id": k, "count": v} for k, v in cwe_counts.items()],
            key=lambda x: x["count"],
            reverse=True,
        )[:5]

        # 5. Calculate Security Health Score
        health_score_data = await self.health_score_service.calculate_for_project(project.id)

        return {
            "project": {
                "id": str(project.id),
                "public_id": project.public_id,
                "name": project.name,
                "description": project.description,
            },
            "organization": {
                "id": str(org.id) if org else None,
                "name": org.name if org else "Default Organization",
            },
            "scan": {
                "id": str(scan.id),
                "public_id": scan.public_id,
                "scan_type": scan.config.get("scan_type", "full") if scan.config else "full",
                "status": scan.status,
                "created_at": scan.created_at.isoformat() if scan.created_at else None,
                "completed_at": scan.completed_at.isoformat() if scan.completed_at else None,
            },
            "snapshot": {
                "id": str(snapshot.id) if snapshot else None,
                "public_id": snapshot.public_id if snapshot else None,
                "commit_sha": snapshot.source_version if snapshot else "HEAD",
                "branch": "main",
                "total_files": snapshot.file_count if snapshot else 0,
                "total_lines": snapshot.total_bytes if snapshot else 0,
            },
            "metrics": {
                "total_findings": len(findings_list),
                "total_occurrences": len(occurrences),
                "severity_counts": severity_counts,
                "status_counts": status_counts,
                "top_cwes": top_cwes,
                "health_score": health_score_data["score"],
                "health_rating": health_score_data["rating"],
                "score_version": health_score_data["version"],
            },
            "findings": findings_list,
        }
