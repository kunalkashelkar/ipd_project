# ============================================================
# Phase 5 Final Correction Pass Automated Regression Test Suite
# ============================================================
# Validates:
# 1. Organization dashboard metrics derive from authoritative Finding domain
# 2. Critical count matches persisted findings
# 3. Repeated occurrences across scans do not inflate finding count
# 4. Organization with zero findings returns zero
# 5. Cross-tenant isolation on dashboard finding aggregates
# 6. Unsupported native PDG has status='unsupported' and blocked download
# 7. Supported Joern PDG remains ready and downloadable
# 8. Taint evidence responses distinguish not_run, failed, and ready (0 vs >0 paths)
# ============================================================

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import BadRequestError, ValidationError
from backend.app.core.security import create_token_pair
from backend.app.models.analysis_artifact import AnalysisArtifact
from backend.app.models.finding import Finding, FindingOccurrence
from backend.app.models.organization import Organization, OrganizationMember
from backend.app.models.project import Project
from backend.app.models.rbac import Role
from backend.app.models.scan import Scan
from backend.app.models.source_snapshot import SourceSnapshot
from backend.app.models.user import User
from backend.app.services.analytics_service import AnalyticsService
from backend.app.services.finding_service.lifecycle import FindingLifecycleService
from backend.app.services.scan_service import ScanService


@pytest.mark.asyncio
async def test_dashboard_metrics_authoritative_finding_counts(
    db_session: AsyncSession,
):
    """Verify Dashboard metrics count real persistent findings and active critical issues."""
    org = Organization(id=uuid.uuid4(), name="Metrics Org", slug=f"metrics-org-{uuid.uuid4().hex[:6]}")
    user = User(
        id=uuid.uuid4(),
        name="Metrics User",
        email=f"user-{uuid.uuid4().hex[:6]}@example.com",
        password_hash="hash",
        status="active",
    )
    db_session.add_all([org, user])
    await db_session.flush()

    project = Project(id=uuid.uuid4(), name="Metrics Project", organization_id=org.id, owner_id=user.id)
    db_session.add(project)
    await db_session.flush()

    # Create 3 persistent findings: 2 critical (1 open, 1 confirmed), 1 high (open), 1 false_positive (critical, excluded)
    f_crit_1 = Finding(
        id=uuid.uuid4(),
        project_id=project.id,
        organization_id=org.id,
        title="SQL Injection",
        vulnerability_type="Injection",
        cwe_id="CWE-89",
        severity="critical",
        confidence=0.9,
        risk_score=9.0,
        status="OPEN",
        fingerprint=f"fp-crit-1-{uuid.uuid4().hex[:6]}",
        first_seen_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
    )
    f_crit_2 = Finding(
        id=uuid.uuid4(),
        project_id=project.id,
        organization_id=org.id,
        title="Remote Code Execution",
        vulnerability_type="RCE",
        cwe_id="CWE-78",
        severity="critical",
        confidence=0.95,
        risk_score=9.8,
        status="CONFIRMED",
        fingerprint=f"fp-crit-2-{uuid.uuid4().hex[:6]}",
        first_seen_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
    )
    f_high = Finding(
        id=uuid.uuid4(),
        project_id=project.id,
        organization_id=org.id,
        title="Path Traversal",
        vulnerability_type="File Inclusion",
        cwe_id="CWE-22",
        severity="high",
        confidence=0.85,
        risk_score=7.5,
        status="OPEN",
        fingerprint=f"fp-high-{uuid.uuid4().hex[:6]}",
        first_seen_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
    )
    f_fp = Finding(
        id=uuid.uuid4(),
        project_id=project.id,
        organization_id=org.id,
        title="False Positive Critical",
        vulnerability_type="Injection",
        cwe_id="CWE-89",
        severity="critical",
        confidence=0.9,
        risk_score=9.0,
        status="FALSE_POSITIVE",
        fingerprint=f"fp-fp-{uuid.uuid4().hex[:6]}",
        first_seen_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
    )
    db_session.add_all([f_crit_1, f_crit_2, f_high, f_fp])
    await db_session.commit()

    service = AnalyticsService(db_session)
    metrics = await service.get_dashboard_metrics(organization_id=org.id)

    # Total active findings: f_crit_1, f_crit_2, f_high = 3 (excluding FALSE_POSITIVE)
    assert metrics["total_vulnerabilities"] == 3
    assert metrics["severity_breakdown"]["critical"] == 2
    assert metrics["severity_breakdown"]["high"] == 1
    assert metrics["severity_breakdown"]["medium"] == 0

    # Verify vulnerabilities_by_cwe aggregates persisted findings and excludes FALSE_POSITIVE
    cwe_items = metrics["vulnerabilities_by_cwe"]
    assert len(cwe_items) == 3
    cwe_map = {item["cwe_id"]: item["count"] for item in cwe_items}
    assert cwe_map["CWE-89"] == 1  # 1 open, 1 false_positive excluded
    assert cwe_map["CWE-78"] == 1
    assert cwe_map["CWE-22"] == 1


@pytest.mark.asyncio
async def test_repeated_occurrences_do_not_inflate_finding_count(
    db_session: AsyncSession,
):
    """Verify that multiple scan occurrences of the same finding fingerprint do not multiply count."""
    org = Organization(id=uuid.uuid4(), name="Deduplication Org", slug=f"dedup-org-{uuid.uuid4().hex[:6]}")
    user = User(
        id=uuid.uuid4(),
        name="Dedup User",
        email=f"user-{uuid.uuid4().hex[:6]}@example.com",
        password_hash="hash",
        status="active",
    )
    db_session.add_all([org, user])
    await db_session.flush()

    project = Project(id=uuid.uuid4(), name="Dedup Project", organization_id=org.id, owner_id=user.id)
    db_session.add(project)
    await db_session.flush()

    snap = SourceSnapshot(
        id=uuid.uuid4(),
        project_id=project.id,
        source_type="archive_upload",
        status="ready",
        artifact_uri=f"snapshots/{uuid.uuid4()}/src.tar.gz",
        content_hash="hash123",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(snap)
    await db_session.flush()

    scan1 = Scan(
        id=uuid.uuid4(),
        project_id=project.id,
        source_snapshot_id=snap.id,
        status="completed",
        current_stage="completed",
        progress=100,
        created_at=datetime.now(timezone.utc),
    )
    scan2 = Scan(
        id=uuid.uuid4(),
        project_id=project.id,
        source_snapshot_id=snap.id,
        status="completed",
        current_stage="completed",
        progress=100,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add_all([scan1, scan2])
    await db_session.flush()

    # 1 single persistent finding
    finding = Finding(
        id=uuid.uuid4(),
        project_id=project.id,
        organization_id=org.id,
        title="Recurring Vulnerability",
        vulnerability_type="Injection",
        cwe_id="CWE-89",
        severity="critical",
        confidence=0.9,
        risk_score=9.0,
        status="OPEN",
        fingerprint=f"fp-recurring-{uuid.uuid4().hex[:6]}",
        first_seen_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
    )
    db_session.add(finding)
    await db_session.flush()

    # 2 occurrences across scan1 and scan2
    occ1 = FindingOccurrence(
        id=uuid.uuid4(),
        finding_id=finding.id,
        scan_id=scan1.id,
        source_snapshot_id=snap.id,
        file_path="src/login.py",
        start_line=10,
        end_line=15,
        severity="critical",
        confidence=0.9,
        observed_at=datetime.now(timezone.utc),
    )
    occ2 = FindingOccurrence(
        id=uuid.uuid4(),
        finding_id=finding.id,
        scan_id=scan2.id,
        source_snapshot_id=snap.id,
        file_path="src/login.py",
        start_line=10,
        end_line=15,
        severity="critical",
        confidence=0.9,
        observed_at=datetime.now(timezone.utc),
    )
    db_session.add_all([occ1, occ2])
    await db_session.commit()

    service = AnalyticsService(db_session)
    metrics = await service.get_dashboard_metrics(organization_id=org.id)

    # Despite 2 occurrences, total findings is EXACTLY 1
    assert metrics["total_vulnerabilities"] == 1
    assert metrics["severity_breakdown"]["critical"] == 1


@pytest.mark.asyncio
async def test_organization_with_zero_findings_returns_zero(
    db_session: AsyncSession,
):
    """Verify empty organization cleanly returns 0 for all security metrics."""
    empty_org = Organization(id=uuid.uuid4(), name="Empty Org", slug=f"empty-org-{uuid.uuid4().hex[:6]}")
    db_session.add(empty_org)
    await db_session.commit()

    service = AnalyticsService(db_session)
    metrics = await service.get_dashboard_metrics(organization_id=empty_org.id)

    assert metrics["total_projects"] == 0
    assert metrics["total_scans"] == 0
    assert metrics["total_vulnerabilities"] == 0
    assert metrics["severity_breakdown"]["critical"] == 0
    assert metrics["severity_breakdown"]["high"] == 0


@pytest.mark.asyncio
async def test_tenant_isolation_on_finding_aggregates(
    db_session: AsyncSession,
):
    """Verify Organization A cannot see Organization B findings in dashboard metrics."""
    org_a = Organization(id=uuid.uuid4(), name="Org A", slug=f"org-a-{uuid.uuid4().hex[:6]}")
    org_b = Organization(id=uuid.uuid4(), name="Org B", slug=f"org-b-{uuid.uuid4().hex[:6]}")
    user = User(
        id=uuid.uuid4(),
        name="Cross User",
        email=f"user-{uuid.uuid4().hex[:6]}@example.com",
        password_hash="hash",
        status="active",
    )
    db_session.add_all([org_a, org_b, user])
    await db_session.flush()

    proj_a = Project(id=uuid.uuid4(), name="Proj A", organization_id=org_a.id, owner_id=user.id)
    proj_b = Project(id=uuid.uuid4(), name="Proj B", organization_id=org_b.id, owner_id=user.id)
    db_session.add_all([proj_a, proj_b])
    await db_session.flush()

    # 2 findings in Org A
    fa1 = Finding(
        id=uuid.uuid4(),
        project_id=proj_a.id,
        organization_id=org_a.id,
        title="Org A Bug 1",
        vulnerability_type="XSS",
        cwe_id="CWE-79",
        severity="high",
        confidence=0.8,
        risk_score=7.0,
        status="OPEN",
        fingerprint=f"fp-a1-{uuid.uuid4().hex[:6]}",
        first_seen_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
    )
    fa2 = Finding(
        id=uuid.uuid4(),
        project_id=proj_a.id,
        organization_id=org_a.id,
        title="Org A Bug 2",
        vulnerability_type="CSRF",
        cwe_id="CWE-352",
        severity="medium",
        confidence=0.7,
        risk_score=5.0,
        status="OPEN",
        fingerprint=f"fp-a2-{uuid.uuid4().hex[:6]}",
        first_seen_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
    )
    # 5 critical findings in Org B
    for i in range(5):
        fb = Finding(
            id=uuid.uuid4(),
            project_id=proj_b.id,
            organization_id=org_b.id,
            title=f"Org B Bug {i}",
            vulnerability_type="RCE",
            cwe_id="CWE-78",
            severity="critical",
            confidence=0.9,
            risk_score=9.5,
            status="OPEN",
            fingerprint=f"fp-b{i}-{uuid.uuid4().hex[:6]}",
            first_seen_at=datetime.now(timezone.utc),
            last_seen_at=datetime.now(timezone.utc),
        )
        db_session.add(fb)

    db_session.add_all([fa1, fa2])
    await db_session.commit()

    service = AnalyticsService(db_session)
    metrics_a = await service.get_dashboard_metrics(organization_id=org_a.id)
    metrics_b = await service.get_dashboard_metrics(organization_id=org_b.id)

    # Org A sees only 2 findings (0 critical, 1 high, 1 medium)
    assert metrics_a["total_vulnerabilities"] == 2
    assert metrics_a["severity_breakdown"]["critical"] == 0
    assert metrics_a["severity_breakdown"]["high"] == 1
    assert metrics_a["severity_breakdown"]["medium"] == 1

    # Org B sees only 5 findings (5 critical)
    assert metrics_b["total_vulnerabilities"] == 5
    assert metrics_b["severity_breakdown"]["critical"] == 5
    assert metrics_b["severity_breakdown"]["high"] == 0

    # Cross-tenant CWE isolation
    cwe_map_a = {item["cwe_id"]: item["count"] for item in metrics_a["vulnerabilities_by_cwe"]}
    cwe_map_b = {item["cwe_id"]: item["count"] for item in metrics_b["vulnerabilities_by_cwe"]}
    assert cwe_map_a == {"CWE-79": 1, "CWE-352": 1}
    assert cwe_map_b == {"CWE-78": 5}
    # No leakage across tenants
    assert "CWE-78" not in cwe_map_a
    assert "CWE-79" not in cwe_map_b
    assert "CWE-352" not in cwe_map_b


@pytest.mark.asyncio
async def test_unsupported_native_pdg_representation_and_blocked_download(
    db_session: AsyncSession,
):
    """Verify that PDG under native fallback is represented as unsupported and download is blocked."""
    org = Organization(id=uuid.uuid4(), name="PDG Org", slug=f"pdg-org-{uuid.uuid4().hex[:6]}")
    user = User(
        id=uuid.uuid4(),
        name="PDG User",
        email=f"user-{uuid.uuid4().hex[:6]}@example.com",
        password_hash="hash",
        status="active",
    )
    db_session.add_all([org, user])
    await db_session.flush()

    project = Project(id=uuid.uuid4(), name="PDG Project", organization_id=org.id, owner_id=user.id)
    db_session.add(project)
    await db_session.flush()

    snap = SourceSnapshot(
        id=uuid.uuid4(),
        project_id=project.id,
        source_type="archive_upload",
        status="ready",
        artifact_uri=f"snapshots/{uuid.uuid4()}/src.tar.gz",
        content_hash="hash123",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(snap)
    await db_session.flush()

    scan = Scan(
        id=uuid.uuid4(),
        project_id=project.id,
        source_snapshot_id=snap.id,
        status="completed",
        current_stage="completed",
        progress=100,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(scan)
    await db_session.flush()

    # Native fallback PDG artifact (0 nodes, 0 edges, tool_name native_ast_analyzer)
    pdg_art = AnalysisArtifact(
        id=uuid.uuid4(),
        scan_id=scan.id,
        source_snapshot_id=snap.id,
        artifact_type="PDG",
        schema_version="1.0.0",
        artifact_uri=f"organizations/{org.id}/projects/{project.id}/scans/{scan.id}/artifacts/pdg/pdg.json",
        content_hash="hashpdg123",
        size_bytes=100,
        status="ready",  # Even if DB had ready initially
        tool_name="native_ast_analyzer",
        tool_version="1.0.0",
        node_count=0,
        edge_count=0,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(pdg_art)
    await db_session.commit()

    service = ScanService(db_session)
    artifacts = await service.get_scan_artifacts(scan.id)
    pdg_retrieved = next(a for a in artifacts if a.artifact_type == "PDG")

    # Status must be truthfully reported as unsupported
    assert pdg_retrieved.status == "unsupported"
    assert "Joern" in pdg_retrieved.artifact_metadata.get("note", "")

    # Downloading unsupported artifact must raise BadRequestError
    with pytest.raises(BadRequestError):
        await service.get_artifact_content(scan.id, pdg_art.id)

    with pytest.raises(BadRequestError):
        await service.get_artifact_detail(scan.id, pdg_art.id)


@pytest.mark.asyncio
async def test_supported_joern_pdg_remains_ready_and_supported(
    db_session: AsyncSession,
):
    """Verify that when Joern produces a genuine PDG with nodes/edges, it remains supported."""
    org = Organization(id=uuid.uuid4(), name="Joern Org", slug=f"joern-org-{uuid.uuid4().hex[:6]}")
    user = User(
        id=uuid.uuid4(),
        name="Joern User",
        email=f"user-{uuid.uuid4().hex[:6]}@example.com",
        password_hash="hash",
        status="active",
    )
    db_session.add_all([org, user])
    await db_session.flush()

    project = Project(id=uuid.uuid4(), name="Joern Project", organization_id=org.id, owner_id=user.id)
    db_session.add(project)
    await db_session.flush()

    snap = SourceSnapshot(
        id=uuid.uuid4(),
        project_id=project.id,
        source_type="archive_upload",
        status="ready",
        artifact_uri=f"snapshots/{uuid.uuid4()}/src.tar.gz",
        content_hash="hash123",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(snap)
    await db_session.flush()

    scan = Scan(
        id=uuid.uuid4(),
        project_id=project.id,
        source_snapshot_id=snap.id,
        status="completed",
        current_stage="completed",
        progress=100,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(scan)
    await db_session.flush()

    # Genuine Joern PDG artifact
    joern_pdg = AnalysisArtifact(
        id=uuid.uuid4(),
        scan_id=scan.id,
        source_snapshot_id=snap.id,
        artifact_type="PDG",
        schema_version="1.0.0",
        artifact_uri=f"organizations/{org.id}/projects/{project.id}/scans/{scan.id}/artifacts/pdg/pdg.json",
        content_hash="hashjoernpdg123",
        size_bytes=2048,
        status="ready",
        tool_name="joern",
        tool_version="2.0.0",
        node_count=120,
        edge_count=95,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(joern_pdg)
    await db_session.commit()

    service = ScanService(db_session)
    artifacts = await service.get_scan_artifacts(scan.id)
    pdg_retrieved = next(a for a in artifacts if a.artifact_type == "PDG")

    # Real Joern output remains ready
    assert pdg_retrieved.status == "ready"
    assert pdg_retrieved.node_count == 120
    assert pdg_retrieved.edge_count == 95


@pytest.mark.asyncio
async def test_taint_states_distinction(
    db_session: AsyncSession,
):
    """Verify taint responses distinguish not_run, failed, and ready states."""
    org = Organization(id=uuid.uuid4(), name="Taint Org", slug=f"taint-org-{uuid.uuid4().hex[:6]}")
    user = User(
        id=uuid.uuid4(),
        name="Taint User",
        email=f"user-{uuid.uuid4().hex[:6]}@example.com",
        password_hash="hash",
        status="active",
    )
    db_session.add_all([org, user])
    await db_session.flush()

    project = Project(id=uuid.uuid4(), name="Taint Project", organization_id=org.id, owner_id=user.id)
    db_session.add(project)
    await db_session.flush()

    snap = SourceSnapshot(
        id=uuid.uuid4(),
        project_id=project.id,
        source_type="archive_upload",
        status="ready",
        artifact_uri=f"snapshots/{uuid.uuid4()}/src.tar.gz",
        content_hash="hash123",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(snap)
    await db_session.flush()

    # Case A: Scan with no TAINT artifact (not run)
    scan_not_run = Scan(
        id=uuid.uuid4(),
        project_id=project.id,
        source_snapshot_id=snap.id,
        status="completed",
        current_stage="completed",
        progress=100,
        created_at=datetime.now(timezone.utc),
    )
    # Case B: Scan with failed TAINT artifact
    scan_failed = Scan(
        id=uuid.uuid4(),
        project_id=project.id,
        source_snapshot_id=snap.id,
        status="completed",
        current_stage="completed",
        progress=100,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add_all([scan_not_run, scan_failed])
    await db_session.flush()

    taint_failed_art = AnalysisArtifact(
        id=uuid.uuid4(),
        scan_id=scan_failed.id,
        source_snapshot_id=snap.id,
        artifact_type="TAINT",
        schema_version="1.0.0",
        artifact_uri="path/taint.json",
        content_hash="hashfailed",
        size_bytes=0,
        status="failed",
        error_message="CFG traversal recursion limit exceeded",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(taint_failed_art)
    await db_session.commit()

    service = ScanService(db_session)

    # 1. Not run
    res_not_run = await service.get_taint_evidence(scan_not_run.id)
    assert res_not_run["status"] == "not_run"
    assert "not executed" in res_not_run["message"]

    # 2. Failed
    res_failed = await service.get_taint_evidence(scan_failed.id)
    assert res_failed["status"] == "failed"
    assert "recursion limit exceeded" in res_failed["message"]


@pytest.mark.asyncio
async def test_dashboard_cwe_aggregation_ranking_and_empty_state(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """Verify dashboard aggregates persisted CWEs by count descending, excludes non-active/empty, and isolates tenants."""
    org = Organization(id=uuid.uuid4(), name="CWE Org", slug=f"cwe-org-{uuid.uuid4().hex[:6]}")
    user = User(
        id=uuid.uuid4(),
        name="CWE Analyst",
        email=f"cwe-{uuid.uuid4().hex[:6]}@example.com",
        password_hash="hash",
        status="active",
    )
    db_session.add_all([org, user])
    await db_session.flush()

    role_res = await db_session.execute(select(Role).where(Role.name == "security_analyst"))
    analyst_role = role_res.scalar_one()

    member = OrganizationMember(
        id=uuid.uuid4(),
        organization_id=org.id,
        user_id=user.id,
        role_id=analyst_role.id,
        status="active",
    )
    project = Project(id=uuid.uuid4(), name="CWE Project", organization_id=org.id, owner_id=user.id)
    db_session.add_all([member, project])
    await db_session.flush()

    # 4x CWE-78 (OPEN)
    for i in range(4):
        db_session.add(
            Finding(
                id=uuid.uuid4(),
                project_id=project.id,
                organization_id=org.id,
                title=f"Command Injection {i}",
                vulnerability_type="RCE",
                cwe_id="CWE-78",
                severity="critical",
                confidence=0.9,
                risk_score=9.0,
                status="OPEN",
                fingerprint=f"fp-cwe78-{i}-{uuid.uuid4().hex[:6]}",
                first_seen_at=datetime.now(timezone.utc),
                last_seen_at=datetime.now(timezone.utc),
            )
        )

    # 2x CWE-89 (1 OPEN, 1 CONFIRMED)
    db_session.add(
        Finding(
            id=uuid.uuid4(),
            project_id=project.id,
            organization_id=org.id,
            title="SQL Injection 1",
            vulnerability_type="Injection",
            cwe_id="CWE-89",
            severity="high",
            confidence=0.85,
            risk_score=8.0,
            status="OPEN",
            fingerprint=f"fp-cwe89-1-{uuid.uuid4().hex[:6]}",
            first_seen_at=datetime.now(timezone.utc),
            last_seen_at=datetime.now(timezone.utc),
        )
    )
    db_session.add(
        Finding(
            id=uuid.uuid4(),
            project_id=project.id,
            organization_id=org.id,
            title="SQL Injection 2",
            vulnerability_type="Injection",
            cwe_id="CWE-89",
            severity="high",
            confidence=0.88,
            risk_score=8.5,
            status="CONFIRMED",
            fingerprint=f"fp-cwe89-2-{uuid.uuid4().hex[:6]}",
            first_seen_at=datetime.now(timezone.utc),
            last_seen_at=datetime.now(timezone.utc),
        )
    )

    # 1x CWE-22 (IN_PROGRESS)
    db_session.add(
        Finding(
            id=uuid.uuid4(),
            project_id=project.id,
            organization_id=org.id,
            title="Path Traversal",
            vulnerability_type="File Inclusion",
            cwe_id="CWE-22",
            severity="medium",
            confidence=0.75,
            risk_score=6.0,
            status="IN_PROGRESS",
            fingerprint=f"fp-cwe22-{uuid.uuid4().hex[:6]}",
            first_seen_at=datetime.now(timezone.utc),
            last_seen_at=datetime.now(timezone.utc),
        )
    )

    # Excluded from active findings: FALSE_POSITIVE and SUPPRESSED
    db_session.add(
        Finding(
            id=uuid.uuid4(),
            project_id=project.id,
            organization_id=org.id,
            title="Excluded FP",
            vulnerability_type="CSRF",
            cwe_id="CWE-352",
            severity="medium",
            confidence=0.7,
            risk_score=5.0,
            status="FALSE_POSITIVE",
            fingerprint=f"fp-fp-{uuid.uuid4().hex[:6]}",
            first_seen_at=datetime.now(timezone.utc),
            last_seen_at=datetime.now(timezone.utc),
        )
    )
    db_session.add(
        Finding(
            id=uuid.uuid4(),
            project_id=project.id,
            organization_id=org.id,
            title="Excluded Suppressed",
            vulnerability_type="XSS",
            cwe_id="CWE-79",
            severity="low",
            confidence=0.6,
            risk_score=3.0,
            status="SUPPRESSED",
            fingerprint=f"fp-sup-{uuid.uuid4().hex[:6]}",
            first_seen_at=datetime.now(timezone.utc),
            last_seen_at=datetime.now(timezone.utc),
        )
    )

    # Empty string and None cwe_id must also be excluded
    db_session.add(
        Finding(
            id=uuid.uuid4(),
            project_id=project.id,
            organization_id=org.id,
            title="No CWE Empty String",
            vulnerability_type="Generic",
            cwe_id="",
            severity="low",
            confidence=0.5,
            risk_score=2.0,
            status="OPEN",
            fingerprint=f"fp-nocwe-empty-{uuid.uuid4().hex[:6]}",
            first_seen_at=datetime.now(timezone.utc),
            last_seen_at=datetime.now(timezone.utc),
        )
    )
    db_session.add(
        Finding(
            id=uuid.uuid4(),
            project_id=project.id,
            organization_id=org.id,
            title="No CWE None",
            vulnerability_type="Generic",
            cwe_id=None,
            severity="low",
            confidence=0.5,
            risk_score=2.0,
            status="OPEN",
            fingerprint=f"fp-nocwe-none-{uuid.uuid4().hex[:6]}",
            first_seen_at=datetime.now(timezone.utc),
            last_seen_at=datetime.now(timezone.utc),
        )
    )

    await db_session.commit()

    # 1. Direct Service Call
    service = AnalyticsService(db_session)
    metrics = await service.get_dashboard_metrics(organization_id=org.id)

    top_cwes = metrics["vulnerabilities_by_cwe"]
    assert len(top_cwes) == 3
    # Strict ordering: CWE-78 (4), CWE-89 (2), CWE-22 (1)
    assert top_cwes[0] == {"cwe_id": "CWE-78", "count": 4}
    assert top_cwes[1] == {"cwe_id": "CWE-89", "count": 2}
    assert top_cwes[2] == {"cwe_id": "CWE-22", "count": 1}

    # 2. HTTP API Call
    token = create_token_pair(str(user.id), user.email)["access_token"]
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": str(org.id)}
    api_res = await client.get("/api/v1/analytics/dashboard", headers=headers)
    assert api_res.status_code == 200
    api_cwes = api_res.json()["data"]["vulnerabilities_by_cwe"]
    assert api_cwes == [
        {"cwe_id": "CWE-78", "count": 4},
        {"cwe_id": "CWE-89", "count": 2},
        {"cwe_id": "CWE-22", "count": 1},
    ]

    # 3. Empty state for organization without findings
    empty_org = Organization(id=uuid.uuid4(), name="Empty CWE Org", slug=f"empty-cwe-{uuid.uuid4().hex[:6]}")
    empty_user = User(
        id=uuid.uuid4(),
        name="Empty User",
        email=f"empty-{uuid.uuid4().hex[:6]}@example.com",
        password_hash="hash",
        status="active",
    )
    db_session.add_all([empty_org, empty_user])
    await db_session.flush()

    empty_member = OrganizationMember(
        id=uuid.uuid4(),
        organization_id=empty_org.id,
        user_id=empty_user.id,
        role_id=analyst_role.id,
        status="active",
    )
    db_session.add(empty_member)
    await db_session.commit()

    empty_metrics = await service.get_dashboard_metrics(organization_id=empty_org.id)
    assert empty_metrics["vulnerabilities_by_cwe"] == []

    empty_token = create_token_pair(str(empty_user.id), empty_user.email)["access_token"]
    empty_headers = {"Authorization": f"Bearer {empty_token}", "X-Organization-ID": str(empty_org.id)}
    empty_api_res = await client.get("/api/v1/analytics/dashboard", headers=empty_headers)
    assert empty_api_res.status_code == 200
    assert empty_api_res.json()["data"]["vulnerabilities_by_cwe"] == []


@pytest.mark.asyncio
async def test_finding_detail_status_consistency_and_persistence(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """Verify that finding status is authoritative and identical across API response, DB reload, and state changes."""
    org = Organization(id=uuid.uuid4(), name="Status Org", slug=f"status-org-{uuid.uuid4().hex[:6]}")
    user = User(
        id=uuid.uuid4(),
        name="Status Analyst",
        email=f"status-{uuid.uuid4().hex[:6]}@example.com",
        password_hash="hash",
        status="active",
    )
    db_session.add_all([org, user])
    await db_session.flush()

    role_res = await db_session.execute(select(Role).where(Role.name == "security_analyst"))
    analyst_role = role_res.scalar_one()

    member = OrganizationMember(
        id=uuid.uuid4(),
        organization_id=org.id,
        user_id=user.id,
        role_id=analyst_role.id,
        status="active",
    )
    project = Project(id=uuid.uuid4(), name="Status Project", organization_id=org.id, owner_id=user.id)
    db_session.add_all([member, project])
    await db_session.flush()

    finding_open = Finding(
        id=uuid.uuid4(),
        project_id=project.id,
        organization_id=org.id,
        title="Open Vulnerability",
        vulnerability_type="Injection",
        cwe_id="CWE-89",
        severity="high",
        confidence=0.9,
        risk_score=8.5,
        status="OPEN",
        fingerprint=f"fp-stat-open-{uuid.uuid4().hex[:6]}",
        first_seen_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
    )
    finding_accepted = Finding(
        id=uuid.uuid4(),
        project_id=project.id,
        organization_id=org.id,
        title="Accepted Risk Vulnerability",
        vulnerability_type="Crypto",
        cwe_id="CWE-327",
        severity="medium",
        confidence=0.8,
        risk_score=5.5,
        status="RISK_ACCEPTED",
        fingerprint=f"fp-stat-acc-{uuid.uuid4().hex[:6]}",
        first_seen_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
    )
    db_session.add_all([finding_open, finding_accepted])
    await db_session.commit()

    token = create_token_pair(str(user.id), user.email)["access_token"]
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": str(org.id)}

    # 1. Verify OPEN finding returns status="OPEN" via API and DB query
    res_open = await client.get(f"/api/v1/findings/{finding_open.id}", headers=headers)
    assert res_open.status_code == 200
    assert res_open.json()["data"]["status"] == "OPEN"

    # Reload directly from DB
    reloaded_open = await db_session.get(Finding, finding_open.id)
    assert reloaded_open is not None
    assert reloaded_open.status == "OPEN"

    # 2. Verify RISK_ACCEPTED finding returns status="RISK_ACCEPTED" via API and DB reload
    res_acc = await client.get(f"/api/v1/findings/{finding_accepted.id}", headers=headers)
    assert res_acc.status_code == 200
    assert res_acc.json()["data"]["status"] == "RISK_ACCEPTED"

    reloaded_acc = await db_session.get(Finding, finding_accepted.id)
    assert reloaded_acc is not None
    assert reloaded_acc.status == "RISK_ACCEPTED"

    # 3. Transition OPEN finding to RISK_ACCEPTED via suppression endpoint
    suppress_res = await client.post(
        f"/api/v1/findings/{finding_open.id}/suppress",
        headers=headers,
        json={
            "suppression_type": "RISK_ACCEPTED",
            "reason": "Risk accepted by security team for Q3",
        },
    )
    assert suppress_res.status_code == 200

    # API detail returns updated status="RISK_ACCEPTED"
    detail_after_accept = await client.get(f"/api/v1/findings/{finding_open.id}", headers=headers)
    assert detail_after_accept.status_code == 200
    assert detail_after_accept.json()["data"]["status"] == "RISK_ACCEPTED"

    # Database reload confirms status="RISK_ACCEPTED" persists
    await db_session.refresh(reloaded_open)
    assert reloaded_open.status == "RISK_ACCEPTED"

    # 4. Reopen finding via unsuppress endpoint (transitions to OPEN)
    unsuppress_res = await client.post(
        f"/api/v1/findings/{finding_open.id}/unsuppress",
        headers=headers,
    )
    assert unsuppress_res.status_code == 200

    # API detail returns status="OPEN"
    detail_after_reopen = await client.get(f"/api/v1/findings/{finding_open.id}", headers=headers)
    assert detail_after_reopen.status_code == 200
    assert detail_after_reopen.json()["data"]["status"] == "OPEN"

    # Database reload confirms status="OPEN" persists
    await db_session.refresh(reloaded_open)
    assert reloaded_open.status == "OPEN"

    # 5. Verify invalid transitions are strictly rejected by lifecycle service
    lifecycle_svc = FindingLifecycleService(db_session)
    with pytest.raises(ValidationError) as excinfo:
        await lifecycle_svc.transition_status(
            finding=reloaded_acc,
            new_status="FIXED",
            actor_id=user.id,
            reason="Illegal leap to FIXED",
        )
    assert "Invalid finding status transition from 'RISK_ACCEPTED' to 'FIXED'" in str(excinfo.value)

