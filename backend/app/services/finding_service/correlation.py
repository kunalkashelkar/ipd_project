# ============================================================
# Finding Correlation and Deduplication Engine (Phase 5)
# ============================================================
# Correlates canonical AIPredictions with static and taint evidence,
# computes deterministic fingerprints, deduplicates across repeated scans,
# calculates risk scores, and persists Finding & FindingOccurrence models.
# ============================================================

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.ai_prediction import AIPrediction
from backend.app.models.finding import (
    Finding,
    FindingOccurrence,
    FindingStatusHistory,
)
from backend.app.models.scan import Scan
from backend.app.models.source_snapshot import SourceSnapshot
from backend.app.services.audit_service import AuditService
from backend.app.services.finding_service.fingerprint import compute_finding_fingerprint
from backend.app.services.finding_service.risk import calculate_risk_score


class FindingCorrelationService:
    """Dedicated service for correlating scan evidence into persistent findings."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.audit = AuditService(db)

    async def correlate_and_persist(
        self,
        *,
        scan: Scan,
        snapshot: SourceSnapshot,
        ai_predictions: list[AIPrediction],
        taint_metadata: dict[str, Any] | None = None,
        graph_artifacts: dict[str, Any] | None = None,
    ) -> list[Finding]:
        """Process predictions and evidence for a scan into findings and occurrences.
        
        Guarantees:
        1. Repeated scans of the same issue update existing Finding and create a new Occurrence.
        2. Different issues create distinct Findings.
        3. Full provenance links are preserved between FindingOccurrence and AIPrediction/evidence.
        """
        now = datetime.now(timezone.utc)
        project_id = scan.project_id
        org_id = scan.organization_id or project_id

        # Index taint paths by sink file and function for correlation
        taint_paths_by_file: dict[str, list[dict[str, Any]]] = {}
        if taint_metadata and "paths" in taint_metadata:
            for path_info in taint_metadata["paths"]:
                sink_f = (path_info.get("sink_file") or "").replace("\\", "/").strip().lower()
                if sink_f:
                    taint_paths_by_file.setdefault(sink_f, []).append(path_info)

        # Collect existing findings for this project to ensure in-memory and DB deduplication
        existing_findings_stmt = select(Finding).where(Finding.project_id == project_id)
        res = await self.db.execute(existing_findings_stmt)
        findings_by_fingerprint: dict[str, Finding] = {
            f.fingerprint: f for f in res.scalars().all()
        }

        persisted_findings: list[Finding] = []

        # Correlate each AI prediction
        for pred in ai_predictions:
            # Only process vulnerable predictions
            if pred.prediction != "VULNERABLE":
                continue

            file_norm = pred.file_path.replace("\\", "/").strip().lower()
            matching_taints = taint_paths_by_file.get(file_norm, [])
            has_taint = len(matching_taints) > 0
            taint_ref = matching_taints[0] if has_taint else None

            # Compute stable fingerprint
            fp, fp_ver = compute_finding_fingerprint(
                cwe_id=pred.cwe_id,
                file_path=pred.file_path,
                function_name=pred.function_name,
                line_number=pred.line_number,
                evidence=pred.evidence_json,
            )

            # Compute versioned risk score
            risk_score, risk_ver = calculate_risk_score(
                severity=pred.severity,
                confidence=pred.confidence,
                cvss_score=pred.cvss_score,
                has_taint_flow=has_taint,
            )

            # Deduplication Check
            existing_finding = findings_by_fingerprint.get(fp)

            if existing_finding:
                # ── Repeated Scan Deduplication ────────────────────────
                # Update last seen timestamp; reopen if previously fixed
                existing_finding.last_seen_at = now
                existing_finding.confidence = max(existing_finding.confidence, pred.confidence)
                existing_finding.risk_score = max(existing_finding.risk_score, risk_score)
                if existing_finding.status in ("FIXED", "VERIFIED"):
                    prev_status = existing_finding.status
                    existing_finding.status = "REOPENED"
                    history = FindingStatusHistory(
                        id=uuid.uuid4(),
                        finding_id=existing_finding.id,
                        previous_status=prev_status,
                        new_status="REOPENED",
                        reason="Vulnerability re-detected in subsequent scan",
                        created_at=now,
                    )
                    self.db.add(history)

                    try:
                        from backend.app.services.notification_service import NotificationService
                        notif_service = NotificationService(self.db)
                        await notif_service.notify_finding_reopened(
                            finding_id=existing_finding.id,
                            finding_public_id=existing_finding.public_id,
                            title=existing_finding.title,
                            organization_id=org_id,
                        )
                    except Exception as re_err:
                        logger.warning("Failed to emit finding_reopened notification: {err}", err=re_err)

                finding_to_link = existing_finding
            else:
                # ── New Finding Creation ───────────────────────────────
                title = (
                    f"{pred.cwe_id or 'Vulnerability'}: "
                    f"{pred.function_name or pred.file_path.split('/')[-1]}"
                )
                if pred.evidence_json and "vulnerability_type" in pred.evidence_json:
                    title = f"{pred.cwe_id or 'Issue'}: {pred.evidence_json['vulnerability_type']}"

                new_finding = Finding(
                    id=uuid.uuid4(),
                    project_id=project_id,
                    organization_id=org_id,
                    title=title,
                    vulnerability_type=pred.cwe_id or "General Vulnerability",
                    cwe_id=pred.cwe_id,
                    severity=pred.severity,
                    cvss_score=pred.cvss_score,
                    confidence=pred.confidence,
                    risk_score=risk_score,
                    risk_version=risk_ver,
                    status="OPEN",
                    fingerprint=fp,
                    fingerprint_version=fp_ver,
                    first_seen_at=now,
                    last_seen_at=now,
                    created_at=now,
                    updated_at=now,
                )
                self.db.add(new_finding)
                findings_by_fingerprint[fp] = new_finding
                finding_to_link = new_finding

                # Initial status history
                init_history = FindingStatusHistory(
                    id=uuid.uuid4(),
                    finding_id=new_finding.id,
                    previous_status=None,
                    new_status="OPEN",
                    actor_id=None,
                    reason="Identified by automated AI and static analysis scan pipeline",
                    created_at=now,
                )
                self.db.add(init_history)

                # Log audit event
                await self.audit.log(
                    user_id=None,
                    action="finding_created",
                    resource_type="finding",
                    resource_id=str(new_finding.id),
                    metadata={
                        "project_id": str(project_id),
                        "scan_id": str(scan.id),
                        "cwe_id": pred.cwe_id,
                        "severity": pred.severity,
                        "fingerprint": fp,
                    },
                )

            # ── Create Immutable FindingOccurrence ─────────────────────
            occurrence = FindingOccurrence(
                id=uuid.uuid4(),
                finding_id=finding_to_link.id,
                scan_id=scan.id,
                source_snapshot_id=snapshot.id,
                file_path=pred.file_path,
                function_name=pred.function_name,
                start_line=pred.line_number,
                end_line=pred.end_line or pred.line_number,
                location={
                    "file_path": pred.file_path,
                    "function_name": pred.function_name,
                    "line": pred.line_number,
                    "end_line": pred.end_line,
                },
                ai_prediction_id=pred.id,
                static_evidence_ref=pred.evidence_json,
                taint_evidence_ref=taint_ref,
                graph_evidence_ref=graph_artifacts,
                confidence=pred.confidence,
                severity=pred.severity,
                observed_at=now,
            )
            self.db.add(occurrence)
            persisted_findings.append(finding_to_link)

        await self.db.flush()
        return list({f.id: f for f in persisted_findings}.values())
