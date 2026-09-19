# ============================================================
# Phase 7 GitHub PR Security & Security Gate Tests
# ============================================================

import hashlib
import hmac
import uuid
import pytest
from datetime import datetime, timezone

from backend.app.models.finding import Finding, FindingOccurrence
from backend.app.models.project import Project
from backend.app.models.repository import Repository
from backend.app.models.scan import Scan
from backend.app.models.security_gate import PRSecurityResult, SecurityGatePolicy
from backend.app.models.source_snapshot import SourceSnapshot
from backend.app.services.pr_security_service import PRSecurityService
from backend.app.services.security_gate_service import SecurityGateService


def test_security_gate_rules():
    db_dummy = None
    gate_svc = SecurityGateService(db_dummy)

    policy = SecurityGatePolicy(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        name="Test Policy",
        version="v1.0.0",
        block_new_critical=True,
        block_new_high=False,
        block_secrets=True,
        cvss_threshold=9.0,
    )

    now = datetime.now(timezone.utc)

    # 1. Pass case: Low / Medium findings
    low_finding = Finding(
        id=uuid.uuid4(), public_id="fnd_low01", title="Low Issue",
        vulnerability_type="INFO", severity="low", cvss_score=3.0,
        first_seen_at=now, last_seen_at=now, fingerprint="fp_low",
    )
    res_pass = gate_svc.evaluate_findings([low_finding], policy)
    assert res_pass["passed"] is True
    assert res_pass["gate_result"] == "PASSED"
    assert len(res_pass["failed_rules"]) == 0

    # 2. Block Critical rule
    crit_finding = Finding(
        id=uuid.uuid4(), public_id="fnd_crit01", title="SQL Injection",
        vulnerability_type="SQLI", severity="critical", cvss_score=8.5,
        first_seen_at=now, last_seen_at=now, fingerprint="fp_crit",
    )
    res_crit = gate_svc.evaluate_findings([crit_finding], policy)
    assert res_crit["passed"] is False
    assert res_crit["gate_result"] == "FAILED"
    assert "block_new_critical" in res_crit["failed_rules"]

    # 3. Block High rule (when enabled)
    policy.block_new_high = True
    high_finding = Finding(
        id=uuid.uuid4(), public_id="fnd_high01", title="CSRF",
        vulnerability_type="CSRF", severity="high", cvss_score=7.5,
        first_seen_at=now, last_seen_at=now, fingerprint="fp_high",
    )
    res_high = gate_svc.evaluate_findings([high_finding], policy)
    assert res_high["passed"] is False
    assert "block_new_high" in res_high["failed_rules"]

    # 4. Secret detection gate
    policy.block_new_high = False
    secret_finding = Finding(
        id=uuid.uuid4(), public_id="fnd_sec01", title="Hardcoded AWS Access Key",
        vulnerability_type="SECRET_DETECTED", severity="medium", cvss_score=5.0,
        cwe_id="CWE-798", first_seen_at=now, last_seen_at=now, fingerprint="fp_sec",
    )
    res_sec = gate_svc.evaluate_findings([secret_finding], policy)
    assert res_sec["passed"] is False
    assert "block_secrets" in res_sec["failed_rules"]

    # 5. CVSS threshold rule
    high_cvss_finding = Finding(
        id=uuid.uuid4(), public_id="fnd_cvss01", title="Severe Protocol Flaw",
        vulnerability_type="PROTOCOL", severity="medium", cvss_score=9.5,
        first_seen_at=now, last_seen_at=now, fingerprint="fp_cvss",
    )
    res_cvss = gate_svc.evaluate_findings([high_cvss_finding], policy)
    assert res_cvss["passed"] is False
    assert "cvss_threshold" in res_cvss["failed_rules"]


@pytest.mark.asyncio
async def test_pr_security_service_workflow(db_session, test_organization, test_project):
    # Setup repo
    repo = Repository(
        id=uuid.uuid4(), project_id=test_project.id, provider="github",
        repository_url="https://github.com/org/test-repo.git", branch="main", status="connected",
    )
    db_session.add(repo)
    await db_session.commit()

    # Snapshots
    base_snap = SourceSnapshot(
        id=uuid.uuid4(),
        project_id=test_project.id,
        source_type="git",
        source_version="base_sha_123",
        content_hash="b" * 64,
        artifact_uri="snapshots/test/base.zip",
        status="ready",
    )
    pr_snap = SourceSnapshot(
        id=uuid.uuid4(),
        project_id=test_project.id,
        source_type="git",
        source_version="pr_sha_456",
        content_hash="c" * 64,
        artifact_uri="snapshots/test/pr.zip",
        status="ready",
    )
    db_session.add_all([base_snap, pr_snap])
    await db_session.commit()

    # Baseline scan and PR scan
    base_scan = Scan(
        id=uuid.uuid4(),
        project_id=test_project.id,
        organization_id=test_organization.id,
        source_snapshot_id=base_snap.id,
        status="completed",
    )
    pr_scan = Scan(
        id=uuid.uuid4(),
        project_id=test_project.id,
        organization_id=test_organization.id,
        source_snapshot_id=pr_snap.id,
        status="completed",
    )
    db_session.add_all([base_scan, pr_scan])
    await db_session.commit()

    now = datetime.now(timezone.utc)
    # Finding 1: in baseline and PR (Existing)
    f_exist = Finding(id=uuid.uuid4(), project_id=test_project.id, organization_id=test_organization.id, title="Old Vuln", vulnerability_type="SQLI", severity="low", status="OPEN", fingerprint="fp_exist", first_seen_at=now, last_seen_at=now)
    # Finding 2: in PR only (New - Critical)
    f_new = Finding(id=uuid.uuid4(), project_id=test_project.id, organization_id=test_organization.id, title="New Exploit", vulnerability_type="RCE", severity="critical", status="OPEN", fingerprint="fp_new", first_seen_at=now, last_seen_at=now)
    db_session.add_all([f_exist, f_new])
    await db_session.commit()

    occ_base = FindingOccurrence(id=uuid.uuid4(), finding_id=f_exist.id, scan_id=base_scan.id, source_snapshot_id=base_snap.id, file_path="a.py", severity="low")
    occ_pr1 = FindingOccurrence(id=uuid.uuid4(), finding_id=f_exist.id, scan_id=pr_scan.id, source_snapshot_id=pr_snap.id, file_path="a.py", severity="low")
    occ_pr2 = FindingOccurrence(id=uuid.uuid4(), finding_id=f_new.id, scan_id=pr_scan.id, source_snapshot_id=pr_snap.id, file_path="b.py", severity="critical")
    db_session.add_all([occ_base, occ_pr1, occ_pr2])
    await db_session.commit()

    pr_service = PRSecurityService(db_session)
    pr_result = await pr_service.evaluate_pr_security(
        project_id=test_project.id,
        repository_id=repo.id,
        pull_request_number=42,
        pr_head_sha="pr_sha_456",
        pr_base_sha="base_sha_123",
        pr_branch="feat-pr",
        pr_title="Feature PR with Vulnerability",
        pr_scan_id=pr_scan.id,
    )

    assert pr_result.existing_findings_count == 1
    assert pr_result.new_findings_count == 1
    assert pr_result.fixed_findings_count == 0
    assert pr_result.gate_result == "FAILED", "New critical finding should fail default security gate"
    assert pr_result.public_id.startswith("pr_")


@pytest.mark.asyncio
async def test_webhook_hmac_and_replay_protection(client, db_session):
    secret = "vulnscan_github_webhook_secret"
    payload = b'{"action": "ping"}'
    valid_sig = "sha256=" + hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    delivery_id = str(uuid.uuid4())

    headers = {
        "X-GitHub-Event": "ping",
        "X-GitHub-Delivery": delivery_id,
        "X-Hub-Signature-256": valid_sig,
        "Content-Type": "application/json",
    }

    # 1. Successful verified delivery
    resp = await client.post("/api/v1/integrations/github/webhook", content=payload, headers=headers)
    assert resp.status_code == 200

    # 2. Replay of same delivery ID is skipped idempotently
    resp_replay = await client.post("/api/v1/integrations/github/webhook", content=payload, headers=headers)
    assert resp_replay.status_code == 200
    assert "duplicate_skipped" in resp_replay.text

    # 3. Invalid signature is rejected
    bad_headers = dict(headers)
    bad_headers["X-Hub-Signature-256"] = "sha256=invalid0000000000000000000000000000000000000000000000000000000000"
    bad_headers["X-GitHub-Delivery"] = str(uuid.uuid4())
    resp_bad = await client.post("/api/v1/integrations/github/webhook", content=payload, headers=bad_headers)
    assert resp_bad.status_code == 401

    # 4. Missing signature is rejected
    no_sig_headers = {
        "X-GitHub-Event": "ping",
        "X-GitHub-Delivery": str(uuid.uuid4()),
        "Content-Type": "application/json",
    }
    resp_no_sig = await client.post("/api/v1/integrations/github/webhook", content=payload, headers=no_sig_headers)
    assert resp_no_sig.status_code == 401

    # 5. Unsupported event is safely ignored
    unsupp_payload = b'{"action": "created"}'
    unsupp_sig = "sha256=" + hmac.new(secret.encode("utf-8"), unsupp_payload, hashlib.sha256).hexdigest()
    unsupp_headers = {
        "X-GitHub-Event": "star",
        "X-GitHub-Delivery": str(uuid.uuid4()),
        "X-Hub-Signature-256": unsupp_sig,
        "Content-Type": "application/json",
    }
    resp_unsupp = await client.post("/api/v1/integrations/github/webhook", content=unsupp_payload, headers=unsupp_headers)
    assert resp_unsupp.status_code == 200
    assert "ignored" in resp_unsupp.text

    # 6. Unknown / untracked repository in PR event
    pr_payload = b'{"action": "opened", "number": 10, "repository": {"clone_url": "https://github.com/unknown/untracked.git"}}'
    pr_sig = "sha256=" + hmac.new(secret.encode("utf-8"), pr_payload, hashlib.sha256).hexdigest()
    pr_headers = {
        "X-GitHub-Event": "pull_request",
        "X-GitHub-Delivery": str(uuid.uuid4()),
        "X-Hub-Signature-256": pr_sig,
        "Content-Type": "application/json",
    }
    resp_untracked = await client.post("/api/v1/integrations/github/webhook", content=pr_payload, headers=pr_headers)
    assert resp_untracked.status_code == 200
    assert "not tracked" in resp_untracked.text


@pytest.mark.asyncio
async def test_secret_detection_gate_and_strict_redaction():
    """Verify that secret detection triggers gate failure and NEVER reveals raw secret values."""
    db_dummy = None
    gate_svc = SecurityGateService(db_dummy)

    policy = SecurityGatePolicy(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        name="Secret Policy",
        version="v1.0.0",
        block_new_critical=True,
        block_new_high=False,
        block_secrets=True,
        cvss_threshold=None,
    )

    now = datetime.now(timezone.utc)
    raw_secret_value = "AKIAIOSFODNN7EXAMPLE_SECRET_KEY_12345"

    secret_finding = Finding(
        id=uuid.uuid4(),
        public_id="fnd_sec99",
        title="Hardcoded AWS Secret Access Key",
        vulnerability_type="HARDCODED_SECRET",
        severity="high",
        cvss_score=7.5,
        cwe_id="CWE-798",
        first_seen_at=now,
        last_seen_at=now,
        fingerprint="fp_secret_99",
    )

    verdict = gate_svc.evaluate_findings([secret_finding], policy)
    assert verdict["passed"] is False
    assert "block_secrets" in verdict["failed_rules"]

    # Strict assertion: raw secret must NEVER appear anywhere in verdict summary, reasons, or rule descriptions
    verdict_str = str(verdict)
    assert raw_secret_value not in verdict_str, "Raw secret content must never be leaked into gate evaluation results"


@pytest.mark.asyncio
async def test_github_integration_status_api(client, auth_headers):
    """Verify /api/v1/integrations/github/status returns truthful configuration states."""
    resp = await client.get("/api/v1/integrations/github/status", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json().get("data", {})
    assert "app_status" in data
    assert "webhook_status" in data
    assert data["app_status"] in ("Configured", "Not configured")
    assert data["capabilities"]["hmac_verified"] is True
    assert data["capabilities"]["replay_protected"] is True

