# ============================================================
# PR Security Service (Phase 7 — PR Scanning, Baseline Comparison, Gates)
# ============================================================

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from loguru import logger
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.core.exceptions import NotFoundError
from backend.app.models.finding import Finding, FindingOccurrence
from backend.app.models.project import Project
from backend.app.models.repository import Repository
from backend.app.models.scan import Scan
from backend.app.models.security_gate import PRSecurityResult, SecurityGatePolicy
from backend.app.services.security_gate_service import SecurityGateService


class PRSecurityService:
    """Orchestrates PR security scanning, baseline comparisons, and gate evaluation."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.gate_service = SecurityGateService(db)

    async def select_baseline_scan(
        self,
        project_id: uuid.UUID,
        repository_id: uuid.UUID,
        base_branch: str | None = "main",
        exclude_scan_id: uuid.UUID | None = None,
    ) -> Scan | None:
        """Deterministic baseline selection rule:
        Find the most recent completed scan for the project on the base branch,
        or fallback to the most recent completed scan on that repository.
        """
        stmt = (
            select(Scan)
            .options(selectinload(Scan.source_snapshot))
            .where(
                Scan.project_id == project_id,
                Scan.status == "completed",
            )
            .order_by(Scan.completed_at.desc(), Scan.created_at.desc())
        )
        if exclude_scan_id:
            stmt = stmt.where(Scan.id != exclude_scan_id)
        res = await self.db.execute(stmt)
        scans = res.scalars().all()

        return scans[0] if scans else None

    async def evaluate_pr_security(
        self,
        *,
        project_id: uuid.UUID,
        repository_id: uuid.UUID,
        pull_request_number: int,
        pr_head_sha: str,
        pr_base_sha: str | None,
        pr_branch: str | None,
        pr_title: str | None,
        pr_scan_id: uuid.UUID,
    ) -> PRSecurityResult:
        """Authoritatively compare PR scan findings against baseline and evaluate security gate."""
        # 1. Resolve project, repository, and baseline
        proj_stmt = select(Project).where(Project.id == project_id)
        project = (await self.db.execute(proj_stmt)).scalar_one_or_none()
        if not project:
            raise NotFoundError(f"Project {project_id} not found")

        baseline_scan = await self.select_baseline_scan(
            project_id=project_id,
            repository_id=repository_id,
            base_branch=pr_branch or "main",
            exclude_scan_id=pr_scan_id,
        )

        # 2. Query PR findings
        pr_occ_stmt = (
            select(FindingOccurrence)
            .options(selectinload(FindingOccurrence.finding))
            .where(FindingOccurrence.scan_id == pr_scan_id)
        )
        pr_occs = (await self.db.execute(pr_occ_stmt)).scalars().all()
        pr_findings_by_fp = {occ.finding.fingerprint: occ.finding for occ in pr_occs if occ.finding}

        # 3. Query Baseline findings
        baseline_fps: set[str] = set()
        if baseline_scan:
            base_occ_stmt = (
                select(FindingOccurrence)
                .options(selectinload(FindingOccurrence.finding))
                .where(FindingOccurrence.scan_id == baseline_scan.id)
            )
            base_occs = (await self.db.execute(base_occ_stmt)).scalars().all()
            baseline_fps = {occ.finding.fingerprint for occ in base_occs if occ.finding}

        pr_fps = set(pr_findings_by_fp.keys())

        # Authoritative classification: Existing, New, Fixed
        existing_fps = pr_fps.intersection(baseline_fps)
        new_fps = pr_fps - baseline_fps
        fixed_fps = baseline_fps - pr_fps

        new_findings = [pr_findings_by_fp[fp] for fp in new_fps]

        # 4. Evaluate Security Gate Policy
        policy = await self.gate_service.get_or_create_policy(project.id, project.organization_id)
        gate_eval = self.gate_service.evaluate_findings(new_findings, policy)

        # 5. Persist PRSecurityResult
        pr_result = PRSecurityResult(
            id=uuid.uuid4(),
            organization_id=project.organization_id,
            project_id=project.id,
            repository_id=repository_id,
            pull_request_number=pull_request_number,
            pr_title=pr_title,
            pr_head_sha=pr_head_sha,
            pr_base_sha=pr_base_sha,
            pr_branch=pr_branch,
            baseline_scan_id=baseline_scan.id if baseline_scan else None,
            pr_scan_id=pr_scan_id,
            existing_findings_count=len(existing_fps),
            new_findings_count=len(new_fps),
            fixed_findings_count=len(fixed_fps),
            gate_result=gate_eval["gate_result"],
            gate_policy_version=policy.version,
            gate_details=gate_eval,
            status="COMPLETED",
            completed_at=datetime.now(timezone.utc),
        )
        self.db.add(pr_result)
        await self.db.commit()
        await self.db.refresh(pr_result)

        logger.info(
            "PR #{pr} security evaluated: Gate={gate} (Existing={e}, New={n}, Fixed={f})",
            pr=pull_request_number,
            gate=pr_result.gate_result,
            e=pr_result.existing_findings_count,
            n=pr_result.new_findings_count,
            f=pr_result.fixed_findings_count,
        )

        return pr_result
