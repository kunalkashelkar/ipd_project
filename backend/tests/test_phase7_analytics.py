# ============================================================
# Phase 7 Analytics Tests
# ============================================================

import uuid
import pytest
from datetime import datetime, timezone, timedelta

from backend.app.models.finding import Finding, FindingOccurrence
from backend.app.models.project import Project
from backend.app.models.scan import Scan
from backend.app.models.source_snapshot import SourceSnapshot
from backend.app.services.analytics_service import AnalyticsService
from backend.app.services.security_health_score import SecurityHealthScoreService


def test_security_health_score_calculation():
    # 1. Perfect score
    res = SecurityHealthScoreService.compute_score_from_counts(
        severity_counts={}, total_findings=0, resolved_findings=0
    )
    assert res["score"] == 100.0
    assert res["rating"] == "A"
    assert res["version"] == "v1.0.0"

    # 2. Critical penalty (-15.0)
    res_crit = SecurityHealthScoreService.compute_score_from_counts(
        severity_counts={"critical": 1}, total_findings=1, resolved_findings=0
    )
    assert res_crit["score"] == 85.0
    assert res_crit["rating"] == "B"

    # 3. High penalty (-8.0) + Medium (-3.0)
    res_hm = SecurityHealthScoreService.compute_score_from_counts(
        severity_counts={"high": 2, "medium": 1}, total_findings=3, resolved_findings=0
    )
    # 100 - (16 + 3) = 81.0
    assert res_hm["score"] == 81.0

    # 4. Severe penalties clamped to 0.0 (Grade F)
    res_f = SecurityHealthScoreService.compute_score_from_counts(
        severity_counts={"critical": 10}, total_findings=10, resolved_findings=0
    )
    assert res_f["score"] == 0.0
    assert res_f["rating"] == "F"

    # 5. Recovery bonus for resolved
    res_rec = SecurityHealthScoreService.compute_score_from_counts(
        severity_counts={"critical": 1}, total_findings=2, resolved_findings=1
    )
    # Base: 100 - 15 + 10*(1/2) = 90.0
    assert res_rec["score"] == 90.0
    assert res_rec["rating"] == "A"


@pytest.mark.asyncio
async def test_analytics_service_metrics(db_session, test_organization, test_project):
    service = AnalyticsService(db_session)

    # 1. Create persistent findings
    now = datetime.now(timezone.utc)
    f1 = Finding(
        id=uuid.uuid4(),
        project_id=test_project.id,
        organization_id=test_organization.id,
        title="Active SQL Injection",
        vulnerability_type="SQLI",
        severity="critical",
        status="OPEN",
        risk_score=90.0,
        fingerprint="fp_test_sqli_001",
        first_seen_at=now,
        last_seen_at=now,
    )
    f2 = Finding(
        id=uuid.uuid4(),
        project_id=test_project.id,
        organization_id=test_organization.id,
        title="Resolved XSS",
        vulnerability_type="XSS",
        severity="high",
        status="FIXED",
        risk_score=70.0,
        fingerprint="fp_test_xss_002",
        first_seen_at=now - timedelta(days=2),
        last_seen_at=now,
        fixed_at=now - timedelta(days=1),
    )
    db_session.add_all([f1, f2])
    await db_session.commit()

    # Setup completed scan so project has security assessment data
    scan = Scan(
        id=uuid.uuid4(),
        project_id=test_project.id,
        organization_id=test_organization.id,
        status="completed",
    )
    db_session.add(scan)
    await db_session.commit()

    # Query metrics
    metrics = await service.get_analytics_metrics(
        organization_id=test_organization.id,
        project_id=test_project.id,
    )

    assert metrics["total_findings"] == 2
    assert metrics["active_findings"] == 1
    assert metrics["resolved_findings"] == 1
    assert metrics["critical_findings"] == 1
    assert metrics["severity_breakdown"]["critical"] == 1
    assert metrics["remediation_rate"] == 0.5
    assert metrics["mttr_hours"] is not None
    assert metrics["health_score"]["version"] == "v1.0.0"
    assert metrics["health_score"]["status"] == "CALCULATED"
    assert metrics["health_score"]["score"] == 90.0
    assert metrics["health_score"]["rating"] == "A"


@pytest.mark.asyncio
async def test_security_health_score_authoritative_contract(db_session, test_organization, test_user):
    """Authoritative regression coverage for Security Health Score semantics:
    1. New organization / no projects / no scans -> NO_DATA
    2. Project with no completed scan -> NO_DATA
    3. Completed scan with zero authoritative findings -> 100/A
    4. Completed scan with findings -> calculated penalty/bonus
    5. False positives/suppressed findings do not penalize
    6. Cross-organization isolation
    7. Same scope returns deterministic result
    """
    health_svc = SecurityHealthScoreService(db_session)

    # 1. New organization with no projects or scans -> NO_DATA
    from backend.app.models.organization import Organization
    empty_org = Organization(id=uuid.uuid4(), name="Empty Workspace Org", slug=f"empty-org-{uuid.uuid4().hex[:8]}")
    db_session.add(empty_org)
    await db_session.commit()

    org_score_empty = await health_svc.calculate_for_organization(empty_org.id)
    assert org_score_empty["status"] == "NO_DATA"
    assert org_score_empty["score"] is None
    assert org_score_empty["rating"] is None
    assert "Run your first security scan" in org_score_empty["message"]

    # 2. Project with no completed scan -> NO_DATA
    proj_unscanned = Project(
        id=uuid.uuid4(),
        organization_id=test_organization.id,
        name="Unscanned Project",
        owner_id=test_user.id,
        language="python",
        is_archived=False,
    )
    db_session.add(proj_unscanned)
    await db_session.commit()

    proj_score_unscanned = await health_svc.calculate_for_project(proj_unscanned.id)
    assert proj_score_unscanned["status"] == "NO_DATA"
    assert proj_score_unscanned["score"] is None
    assert proj_score_unscanned["rating"] is None

    # 3. Completed scan with zero authoritative findings -> 100/A
    proj_clean = Project(
        id=uuid.uuid4(),
        organization_id=test_organization.id,
        name="Clean Project",
        owner_id=test_user.id,
        language="c",
        is_archived=False,
    )
    scan_clean = Scan(
        id=uuid.uuid4(),
        project_id=proj_clean.id,
        organization_id=test_organization.id,
        status="completed",
    )
    db_session.add_all([proj_clean, scan_clean])
    await db_session.commit()

    proj_score_clean = await health_svc.calculate_for_project(proj_clean.id)
    assert proj_score_clean["status"] == "CALCULATED"
    assert proj_score_clean["score"] == 100.0
    assert proj_score_clean["rating"] == "A"
    assert proj_score_clean["penalties_applied"] == 0.0

    # 4. Completed scan with findings -> calculated penalty/bonus
    proj_vuln = Project(
        id=uuid.uuid4(),
        organization_id=test_organization.id,
        name="Vulnerable Project",
        owner_id=test_user.id,
        language="c",
        is_archived=False,
    )
    scan_vuln = Scan(
        id=uuid.uuid4(),
        project_id=proj_vuln.id,
        organization_id=test_organization.id,
        status="completed",
    )
    now_ts = datetime.now(timezone.utc)
    # Add 1 Critical (-15) and 1 High (-8) -> base 100 - 23 = 77.0 (Grade C)
    f_crit = Finding(
        id=uuid.uuid4(),
        project_id=proj_vuln.id,
        organization_id=test_organization.id,
        title="Critical RCE",
        vulnerability_type="RCE",
        severity="critical",
        status="OPEN",
        risk_score=95.0,
        fingerprint="fp_test_rce_001",
        first_seen_at=now_ts,
        last_seen_at=now_ts,
    )
    f_high = Finding(
        id=uuid.uuid4(),
        project_id=proj_vuln.id,
        organization_id=test_organization.id,
        title="High Auth Bypass",
        vulnerability_type="AUTH",
        severity="high",
        status="OPEN",
        risk_score=80.0,
        fingerprint="fp_test_auth_002",
        first_seen_at=now_ts,
        last_seen_at=now_ts,
    )
    db_session.add_all([proj_vuln, scan_vuln, f_crit, f_high])
    await db_session.commit()

    score_vuln = await health_svc.calculate_for_project(proj_vuln.id)
    assert score_vuln["status"] == "CALCULATED"
    assert score_vuln["score"] == 77.0
    assert score_vuln["rating"] == "C"
    assert score_vuln["penalties_applied"] == 23.0

    # 5. False positives / suppressed findings do not penalize
    f_fp = Finding(
        id=uuid.uuid4(),
        project_id=proj_vuln.id,
        organization_id=test_organization.id,
        title="FP Finding",
        vulnerability_type="XSS",
        severity="critical",
        status="FALSE_POSITIVE",
        risk_score=90.0,
        fingerprint="fp_test_fp_003",
        first_seen_at=now_ts,
        last_seen_at=now_ts,
    )
    f_supp = Finding(
        id=uuid.uuid4(),
        project_id=proj_vuln.id,
        organization_id=test_organization.id,
        title="Suppressed Finding",
        vulnerability_type="SQLI",
        severity="critical",
        status="SUPPRESSED",
        risk_score=90.0,
        fingerprint="fp_test_supp_004",
        first_seen_at=now_ts,
        last_seen_at=now_ts,
    )
    db_session.add_all([f_fp, f_supp])
    await db_session.commit()

    score_vuln_fp = await health_svc.calculate_for_project(proj_vuln.id)
    # Score should remain exactly 77.0 because FALSE_POSITIVE and SUPPRESSED are not active
    assert score_vuln_fp["score"] == 77.0
    assert score_vuln_fp["penalties_applied"] == 23.0

    # 6. Cross-organization isolation: Other org cannot see proj_vuln score or findings
    other_org_calc = await health_svc.calculate_for_organization(empty_org.id)
    assert other_org_calc["status"] == "NO_DATA"
    assert other_org_calc["score"] is None

    # 7. Same scope returns deterministic result
    deterministic_run = await health_svc.calculate_for_project(proj_vuln.id)
    assert deterministic_run == score_vuln_fp


@pytest.mark.asyncio
async def test_analytics_scan_comparison(db_session, test_organization, test_project):
    service = AnalyticsService(db_session)

    snapshot = SourceSnapshot(
        id=uuid.uuid4(),
        project_id=test_project.id,
        source_type="git",
        source_version="base123",
        content_hash="b" * 64,
        artifact_uri="snapshots/test/base.zip",
        status="ready",
    )
    db_session.add(snapshot)
    await db_session.commit()

    scan_a = Scan(
        id=uuid.uuid4(),
        project_id=test_project.id,
        organization_id=test_organization.id,
        source_snapshot_id=snapshot.id,
        status="completed",
    )
    scan_b = Scan(
        id=uuid.uuid4(),
        project_id=test_project.id,
        organization_id=test_organization.id,
        source_snapshot_id=snapshot.id,
        status="completed",
    )
    db_session.add_all([scan_a, scan_b])
    await db_session.commit()

    now = datetime.now(timezone.utc)
    # Finding 1: in both scans (Existing)
    f1 = Finding(
        id=uuid.uuid4(), project_id=test_project.id, organization_id=test_organization.id,
        title="Existing Finding", vulnerability_type="SQLI", severity="high", status="OPEN",
        fingerprint="fp_shared_001", first_seen_at=now, last_seen_at=now,
    )
    # Finding 2: in Scan A only (Fixed in Scan B)
    f2 = Finding(
        id=uuid.uuid4(), project_id=test_project.id, organization_id=test_organization.id,
        title="Fixed Finding", vulnerability_type="XSS", severity="medium", status="FIXED",
        fingerprint="fp_fixed_002", first_seen_at=now, last_seen_at=now, fixed_at=now,
    )
    # Finding 3: in Scan B only (New in Scan B)
    f3 = Finding(
        id=uuid.uuid4(), project_id=test_project.id, organization_id=test_organization.id,
        title="New Finding", vulnerability_type="RCE", severity="critical", status="OPEN",
        fingerprint="fp_new_003", first_seen_at=now, last_seen_at=now,
    )
    db_session.add_all([f1, f2, f3])
    await db_session.commit()

    # Link occurrences
    occ_a1 = FindingOccurrence(id=uuid.uuid4(), finding_id=f1.id, scan_id=scan_a.id, source_snapshot_id=snapshot.id, file_path="a.py", severity="high")
    occ_a2 = FindingOccurrence(id=uuid.uuid4(), finding_id=f2.id, scan_id=scan_a.id, source_snapshot_id=snapshot.id, file_path="b.py", severity="medium")
    occ_b1 = FindingOccurrence(id=uuid.uuid4(), finding_id=f1.id, scan_id=scan_b.id, source_snapshot_id=snapshot.id, file_path="a.py", severity="high")
    occ_b3 = FindingOccurrence(id=uuid.uuid4(), finding_id=f3.id, scan_id=scan_b.id, source_snapshot_id=snapshot.id, file_path="c.py", severity="critical")
    db_session.add_all([occ_a1, occ_a2, occ_b1, occ_b3])
    await db_session.commit()

    # 1. Compare using internal UUIDs
    comparison = await service.compare_scans(
        baseline_scan_id=scan_a.id,
        current_scan_id=scan_b.id,
        org_id=test_organization.id,
    )
    assert comparison["existing_count"] == 1
    assert comparison["new_count"] == 1
    assert comparison["fixed_count"] == 1
    assert comparison["existing_findings"][0]["fingerprint"] == "fp_shared_001"
    assert comparison["new_findings"][0]["fingerprint"] == "fp_new_003"
    assert comparison["fixed_findings"][0]["fingerprint"] == "fp_fixed_002"

    # 2. Compare using public identifiers (public + public)
    comp_public = await service.compare_scans(
        baseline_scan_id=scan_a.public_id,
        current_scan_id=scan_b.public_id,
        org_id=test_organization.id,
    )
    assert comp_public["new_count"] == 1
    assert comp_public["fixed_count"] == 1

    # 3. Compare using mixed identifiers (UUID + public)
    comp_mixed = await service.compare_scans(
        baseline_scan_id=str(scan_a.id),
        current_scan_id=scan_b.public_id,
        org_id=test_organization.id,
    )
    assert comp_mixed["new_count"] == 1

    # 4. Cross-project scan comparison must raise BadRequestError with safe actionable cause
    from backend.app.core.exceptions import BadRequestError, NotFoundError
    other_project = Project(
        id=uuid.uuid4(),
        organization_id=test_organization.id,
        name="Other Project",
        owner_id=test_project.owner_id,
        language="python",
        is_archived=False,
    )
    db_session.add(other_project)
    await db_session.commit()

    other_scan = Scan(
        id=uuid.uuid4(),
        project_id=other_project.id,
        organization_id=test_organization.id,
        source_snapshot_id=snapshot.id,
        status="completed",
    )
    db_session.add(other_scan)
    await db_session.commit()

    with pytest.raises(BadRequestError) as exc_info:
        await service.compare_scans(
            baseline_scan_id=scan_a.id,
            current_scan_id=other_scan.id,
            org_id=test_organization.id,
        )
    assert "different projects" in str(exc_info.value)
    assert exc_info.value.code == "BAD_REQUEST"

    # 5. Cross-tenant scan comparison must raise NotFoundError
    other_org_id = uuid.uuid4()
    with pytest.raises(NotFoundError):
        await service.compare_scans(
            baseline_scan_id=scan_a.id,
            current_scan_id=scan_b.id,
            org_id=other_org_id,
        )

    # 6. Incomplete scan must raise BadRequestError
    pending_scan = Scan(
        id=uuid.uuid4(),
        project_id=test_project.id,
        organization_id=test_organization.id,
        source_snapshot_id=snapshot.id,
        status="running",
    )
    db_session.add(pending_scan)
    await db_session.commit()

    with pytest.raises(BadRequestError) as inc_exc:
        await service.compare_scans(
            baseline_scan_id=scan_a.id,
            current_scan_id=pending_scan.id,
            org_id=test_organization.id,
        )
    assert "completed status" in str(inc_exc.value)


@pytest.mark.asyncio
async def test_error_contract_structure(client, test_organization, test_project, auth_headers):
    """Verify structured error contract conforms to {error: {code, message, details, request_id}}."""
    # 1. Trigger a 404
    resp_404 = await client.get("/api/v1/scans/scn_nonexistent99999", headers=auth_headers)
    assert resp_404.status_code == 404
    body_404 = resp_404.json()
    assert "error" in body_404
    assert body_404["error"]["code"] == "NOT_FOUND"
    assert "request_id" in body_404["error"]

    # 2. Trigger a 422 validation error
    resp_422 = await client.post("/api/v1/projects", json={}, headers=auth_headers)
    assert resp_422.status_code == 422
    body_422 = resp_422.json()
    assert "error" in body_422
    assert body_422["error"]["code"] == "VALIDATION_FAILED"
    assert len(body_422["error"]["details"]) > 0
    assert "request_id" in body_422["error"]

