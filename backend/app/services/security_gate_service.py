# ============================================================
# Security Gate Service (Phase 7 — Policy Evaluation Engine)
# ============================================================

from __future__ import annotations

import re
import uuid
from typing import Any, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.finding import Finding
from backend.app.models.security_gate import SecurityGatePolicy


class SecurityGateService:
    """Evaluates project security policies against new scan findings."""

    SECRET_VULN_TYPES = {
        "SECRET",
        "HARDCODED_CREDENTIAL",
        "CREDENTIAL_LEAK",
        "API_KEY_LEAK",
        "SECRET_DETECTED",
    }
    SECRET_CWES = {"CWE-798", "CWE-259", "CWE-321"}

    # Deterministic regex patterns for secret detection in static evidence or code snippets
    SECRET_PATTERNS = [
        re.compile(r"(?i)(?:api[_-]?key|access[_-]?token|secret[_-]?key|bearer)\s*[:=]\s*['\"][a-zA-Z0-9_\-\.]{16,}['\"]"),
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
        re.compile(r"(?i)(?:postgres|mysql|mongodb|redis):\/\/[a-zA-Z0-9_\-]+:[a-zA-Z0-9_\-\.\@]+@"),
        re.compile(r"AKIA[0-9A-Z]{16}"),  # AWS Access Key ID format
    ]

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_policy(
        self, project_id: uuid.UUID, organization_id: uuid.UUID
    ) -> SecurityGatePolicy:
        """Fetch project gate policy or create default."""
        stmt = select(SecurityGatePolicy).where(SecurityGatePolicy.project_id == project_id)
        res = await self.db.execute(stmt)
        policy = res.scalar_one_or_none()
        if not policy:
            policy = SecurityGatePolicy(
                id=uuid.uuid4(),
                project_id=project_id,
                organization_id=organization_id,
                name="Default Security Gate",
                version="v1.0.0",
                block_new_critical=True,
                block_new_high=False,
                block_secrets=True,
                cvss_threshold=None,
            )
            self.db.add(policy)
            await self.db.commit()
            await self.db.refresh(policy)
        return policy

    def is_secret_finding(self, finding: Finding) -> bool:
        """Deterministic secret identification without exposing values."""
        v_type = (finding.vulnerability_type or "").upper()
        if v_type in self.SECRET_VULN_TYPES or "SECRET" in v_type or "KEY" in v_type:
            return True

        cwe = (finding.cwe_id or "").upper()
        if cwe in self.SECRET_CWES:
            return True

        title = (finding.title or "").upper()
        if "HARDCODED" in title or "SECRET" in title or "API KEY" in title:
            return True

        return False

    def evaluate_findings(
        self,
        new_findings: Sequence[Finding],
        policy: SecurityGatePolicy,
    ) -> dict[str, Any]:
        """Evaluate gate policy rules strictly against NEW findings."""
        failed_rules = []
        violations = []

        critical_count = 0
        high_count = 0
        secrets_count = 0
        cvss_violations_count = 0

        for f in new_findings:
            sev = (f.severity or "").lower()
            cvss = f.cvss_score or 0.0

            # Rule 1: Block new Critical
            if policy.block_new_critical and sev == "critical":
                critical_count += 1
                violations.append({
                    "rule": "block_new_critical",
                    "finding_id": f.public_id,
                    "title": f.title,
                    "severity": f.severity,
                })

            # Rule 2: Block new High
            if policy.block_new_high and sev == "high":
                high_count += 1
                violations.append({
                    "rule": "block_new_high",
                    "finding_id": f.public_id,
                    "title": f.title,
                    "severity": f.severity,
                })

            # Rule 3: Block detected Secrets
            if policy.block_secrets and self.is_secret_finding(f):
                secrets_count += 1
                violations.append({
                    "rule": "block_secrets",
                    "finding_id": f.public_id,
                    "title": "Secret / Credential Detected (Value Redacted)",
                    "severity": f.severity,
                })

            # Rule 4: CVSS threshold
            if policy.cvss_threshold is not None and cvss >= policy.cvss_threshold:
                cvss_violations_count += 1
                violations.append({
                    "rule": "cvss_threshold",
                    "finding_id": f.public_id,
                    "title": f.title,
                    "cvss_score": cvss,
                    "threshold": policy.cvss_threshold,
                })

        if critical_count > 0:
            failed_rules.append("block_new_critical")
        if high_count > 0:
            failed_rules.append("block_new_high")
        if secrets_count > 0:
            failed_rules.append("block_secrets")
        if cvss_violations_count > 0:
            failed_rules.append("cvss_threshold")

        passed = len(failed_rules) == 0

        summary = (
            "VulnScan Security Gate Passed: No blocking vulnerabilities detected in PR."
            if passed
            else f"VulnScan Security Gate Failed: {len(violations)} blocking condition(s) triggered."
        )

        return {
            "passed": passed,
            "gate_result": "PASSED" if passed else "FAILED",
            "policy_version": policy.version,
            "failed_rules": failed_rules,
            "violations_count": len(violations),
            "violations": violations,
            "summary": summary,
            "details": {
                "critical_violations": critical_count,
                "high_violations": high_count,
                "secret_violations": secrets_count,
                "cvss_violations": cvss_violations_count,
            },
        }
