# ============================================================
# Phase 5: AI Inference Provider, Vulnerability Finding Domain,
# Deduplication, Lifecycle & Results APIs Automated Test Suite
# ============================================================

from __future__ import annotations

import inspect
import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.security import create_token_pair
from backend.app.models.ai_prediction import AIPrediction
from backend.app.models.finding import (
    Finding,
    FindingAssignment,
    FindingComment,
    FindingOccurrence,
    FindingStatusHistory,
    FindingSuppression,
)
from backend.app.models.organization import Organization, OrganizationMember
from backend.app.models.project import Project
from backend.app.models.rbac import Role
from backend.app.models.scan import Scan
from backend.app.models.source_snapshot import Function, SourceFile, SourceSnapshot
from backend.app.models.user import User
from backend.app.services.ai_inference import (
    AIErrorCode,
    AIInferenceError,
    CanonicalAIRequest,
    FunctionContext,
    SourceFileContext,
    get_ai_provider,
)
from backend.app.services.ai_inference.base import AIInferenceProvider
from backend.app.services.ai_inference.experimental_gcb_provider import (
    ExperimentalGraphCodeBERTProvider,
)
from backend.app.services.ai_inference.mock_provider import MockAIProvider
from backend.app.services.finding_service.correlation import FindingCorrelationService
from backend.app.services.finding_service.fingerprint import compute_finding_fingerprint
from backend.app.services.finding_service.lifecycle import FindingLifecycleService
from backend.app.services.finding_service.risk import calculate_risk_score
from backend.app.storage.service import StorageService


# ── Test 1: AI Provider Boundary & Factory Isolation ─────────


@pytest.mark.asyncio
async def test_ai_provider_boundary_and_factory():
    """Verify AI provider interface, mock isolation, and factory routing."""
    # 1. Factory returns MockAIProvider by default or explicit "mock"
    mock_p = get_ai_provider("mock")
    assert isinstance(mock_p, AIInferenceProvider)
    assert isinstance(mock_p, MockAIProvider)
    assert mock_p.provider_id == "mock"
    assert mock_p.model_name == "MockAIProvider"
    assert "v1.0.0" in mock_p.model_version or "mock" in mock_p.model_version

    meta = mock_p.get_metadata()
    assert meta["provider_id"] == "mock"

    # 2. Unsupported provider raises structured AIInferenceError (no silent fallback to mock)
    with pytest.raises(AIInferenceError) as exc_info:
        get_ai_provider("unsupported_future_provider")
    assert exc_info.value.code == AIErrorCode.PROVIDER_UNAVAILABLE

    # 3. Experimental GraphCodeBERT adapter raises MODEL_NOT_READY when weights absent
    gcb_p = get_ai_provider("graphcodebert")
    assert isinstance(gcb_p, ExperimentalGraphCodeBERTProvider)
    req = CanonicalAIRequest(
        scan_id=uuid.uuid4(),
        source_snapshot_id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        language="python",
    )
    with pytest.raises(AIInferenceError) as gcb_exc:
        await gcb_p.predict(req)
    assert gcb_exc.value.code == AIErrorCode.MODEL_NOT_READY


# ── Test 2: MockAIProvider Determinism & Location Validity ───


@pytest.mark.asyncio
async def test_mock_provider_deterministic_and_location_valid():
    """Verify MockAIProvider generates valid locations within real files/functions."""
    provider = MockAIProvider()
    snap_id = uuid.uuid4()
    scan_id = uuid.uuid4()

    files = [
        SourceFileContext(
            file_id=uuid.uuid4(),
            relative_path="backend/app/routes/auth.py",
            language="python",
            line_count=120,
            content_hash="abc123hash",
            original_artifact_uri="snapshots/snap-1/auth.py",
        ),
        SourceFileContext(
            file_id=uuid.uuid4(),
            relative_path="backend/app/db/query.py",
            language="python",
            line_count=85,
            content_hash="def456hash",
            original_artifact_uri="snapshots/snap-1/query.py",
        ),
    ]

    funcs = [
        FunctionContext(
            function_id="fn-1",
            name="execute_user_query",
            relative_path="backend/app/db/query.py",
            start_line=20,
            end_line=45,
            signature="def execute_user_query(sql_text: str)",
            token_count=120,
        ),
        FunctionContext(
            function_id="fn-2",
            name="login_handler",
            relative_path="backend/app/routes/auth.py",
            start_line=15,
            end_line=60,
            signature="def login_handler(creds: Credentials)",
            token_count=180,
        ),
    ]

    req = CanonicalAIRequest(
        scan_id=scan_id,
        source_snapshot_id=snap_id,
        project_id=uuid.uuid4(),
        language="python",
        source_files=files,
        functions=funcs,
    )

    preds1 = await provider.predict(req)
    assert len(preds1) > 0

    # Verify all predictions target real files and line spans within the function
    for p in preds1:
        assert p.file_path in ["backend/app/routes/auth.py", "backend/app/db/query.py"]
        assert p.prediction == "VULNERABLE"
        assert p.severity in ["critical", "high", "medium", "low"]
        assert p.confidence >= 0.5
        assert p.cwe_id.startswith("CWE-")
        assert p.provider == "mock"
        assert p.generated_by_ai is True

        if p.function_name == "execute_user_query":
            assert 20 <= p.line_number <= 45

    # Determinism: running with identical request yields identical predictions
    preds2 = await provider.predict(req)
    assert len(preds1) == len(preds2)
    for p1, p2 in zip(preds1, preds2):
        assert p1.file_path == p2.file_path
        assert p1.cwe_id == p2.cwe_id
        assert p1.line_number == p2.line_number
        assert p1.confidence == p2.confidence


# ── Test 3: Fingerprinting & Versioned Risk Calculation ──────


def test_fingerprinting_and_risk_calculation():
    """Verify deterministic finding fingerprinting and versioned risk scoring."""
    # 1. Fingerprint calculation
    fp1, ver1 = compute_finding_fingerprint(
        cwe_id="CWE-89",
        file_path="backend/app/db/query.py",
        function_name="execute_user_query",
        line_number=32,
    )
    assert ver1 == "v1.0"
    assert len(fp1) == 64  # sha256 hex string

    # Same inputs yield identical fingerprint
    fp2, _ = compute_finding_fingerprint(
        cwe_id="CWE-89",
        file_path="backend/app/db/query.py",
        function_name="execute_user_query",
        line_number=32,
    )
    assert fp1 == fp2

    # Different CWE yields different fingerprint
    fp3, _ = compute_finding_fingerprint(
        cwe_id="CWE-79",
        file_path="backend/app/db/query.py",
        function_name="execute_user_query",
        line_number=32,
    )
    assert fp1 != fp3

    # 2. Risk score calculation
    risk_score, r_ver = calculate_risk_score(
        severity="critical",
        confidence=0.95,
        cvss_score=9.8,
        has_taint_flow=True,
    )
    assert r_ver == "v1.0"
    assert 8.0 <= risk_score <= 10.0

    low_score, _ = calculate_risk_score(
        severity="low",
        confidence=0.60,
        cvss_score=3.0,
        has_taint_flow=False,
    )
    assert low_score < risk_score


# ── Test 4: Repeated Scan Deduplication ──────────────────────


@pytest.mark.asyncio
async def test_repeated_scan_deduplication(db_session: AsyncSession):
    """Mandatory test: Scanning same source twice yields 1 Finding and 2 Occurrences."""
    user = User(id=uuid.uuid4(), name="Test User", email="test@example.com", password_hash="hash", status="active")
    db_session.add(user)
    org = Organization(id=uuid.uuid4(), name="Test Org", slug="test-org")
    db_session.add(org)
    project = Project(id=uuid.uuid4(), name="Test Project", organization_id=org.id, owner_id=user.id)
    db_session.add(project)

    snap = SourceSnapshot(
        id=uuid.uuid4(),
        project_id=project.id,
        source_type="upload_zip",
        content_hash="test_snap_hash_1",
        artifact_uri="snapshots/snap1.zip",
        status="ready",
    )
    db_session.add(snap)

    scan1 = Scan(
        id=uuid.uuid4(),
        project_id=project.id,
        organization_id=org.id,
        source_snapshot_id=snap.id,
        status="completed",
    )
    scan2 = Scan(
        id=uuid.uuid4(),
        project_id=project.id,
        organization_id=org.id,
        source_snapshot_id=snap.id,
        status="completed",
    )
    db_session.add_all([scan1, scan2])
    await db_session.commit()

    # Create synthetic AIPrediction for Scan 1
    pred1 = AIPrediction(
        id=uuid.uuid4(),
        scan_id=scan1.id,
        source_snapshot_id=snap.id,
        file_path="app/views.py",
        function_name="render_template",
        line_number=45,
        prediction="VULNERABLE",
        confidence=0.92,
        cwe_id="CWE-79",
        severity="high",
        cvss_score=7.5,
        provider="mock",
        model_name="MockAIProvider",
        model_version="v1.0.0",
        evidence_json={"vulnerability_type": "Cross-Site Scripting"},
    )
    db_session.add(pred1)
    await db_session.commit()

    correlation_svc = FindingCorrelationService(db_session)

    # ── Execute Scan 1 correlation ─────────────────────────────
    findings_scan1 = await correlation_svc.correlate_and_persist(
        scan=scan1,
        snapshot=snap,
        ai_predictions=[pred1],
    )
    await db_session.commit()

    assert len(findings_scan1) == 1
    f1 = findings_scan1[0]
    assert f1.status == "OPEN"
    assert f1.cwe_id == "CWE-79"

    # Verify 1 occurrence for Scan 1
    occ_res1 = await db_session.execute(
        select(FindingOccurrence).where(FindingOccurrence.finding_id == f1.id)
    )
    occs1 = occ_res1.scalars().all()
    assert len(occs1) == 1
    assert occs1[0].scan_id == scan1.id

    # ── Execute Scan 2 with same vulnerability ─────────────────
    pred2 = AIPrediction(
        id=uuid.uuid4(),
        scan_id=scan2.id,
        source_snapshot_id=snap.id,
        file_path="app/views.py",
        function_name="render_template",
        line_number=45,
        prediction="VULNERABLE",
        confidence=0.94,
        cwe_id="CWE-79",
        severity="high",
        cvss_score=7.5,
        provider="mock",
        model_name="MockAIProvider",
        model_version="v1.0.0",
        evidence_json={"vulnerability_type": "Cross-Site Scripting"},
    )
    db_session.add(pred2)
    await db_session.commit()

    findings_scan2 = await correlation_svc.correlate_and_persist(
        scan=scan2,
        snapshot=snap,
        ai_predictions=[pred2],
    )
    await db_session.commit()

    # ── Verify Deduplication Guarantee ────────────────────────
    # 1. Total findings count in project remains 1 (NOT 2)
    all_findings_res = await db_session.execute(
        select(Finding).where(Finding.project_id == project.id)
    )
    all_findings = all_findings_res.scalars().all()
    assert len(all_findings) == 1
    assert all_findings[0].id == f1.id

    # 2. Total occurrences is now 2 (one per scan)
    occ_res2 = await db_session.execute(
        select(FindingOccurrence).where(FindingOccurrence.finding_id == f1.id)
    )
    occs2 = occ_res2.scalars().all()
    assert len(occs2) == 2
    scan_ids = {o.scan_id for o in occs2}
    assert scan1.id in scan_ids
    assert scan2.id in scan_ids


# ── Test 5: Lifecycle State Machine Transitions ──────────────


@pytest.mark.asyncio
async def test_finding_lifecycle_transitions(db_session: AsyncSession):
    """Verify valid and invalid finding status transitions."""
    user = User(id=uuid.uuid4(), name="Lifecycle User", email="lifecycle@example.com", password_hash="hash", status="active")
    db_session.add(user)
    org = Organization(id=uuid.uuid4(), name="Lifecycle Org", slug="lifecycle-org")
    db_session.add(org)
    project = Project(id=uuid.uuid4(), name="Lifecycle Project", organization_id=org.id, owner_id=user.id)
    db_session.add(project)

    finding = Finding(
        id=uuid.uuid4(),
        project_id=project.id,
        organization_id=org.id,
        title="SQL Injection in auth",
        vulnerability_type="SQL Injection",
        cwe_id="CWE-89",
        severity="critical",
        confidence=0.95,
        risk_score=9.5,
        status="OPEN",
        fingerprint="test_fp_lifecycle",
        first_seen_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
    )
    db_session.add(finding)
    await db_session.commit()

    lifecycle_svc = FindingLifecycleService(db_session)

    # 1. Valid transitions: OPEN -> CONFIRMED -> IN_PROGRESS -> FIXED
    h1 = await lifecycle_svc.transition_status(finding, "CONFIRMED", reason="Verified by analyst")
    assert finding.status == "CONFIRMED"
    assert h1.new_status == "CONFIRMED"

    h2 = await lifecycle_svc.transition_status(finding, "IN_PROGRESS", reason="Patching started")
    assert finding.status == "IN_PROGRESS"

    h3 = await lifecycle_svc.transition_status(finding, "FIX_PROPOSED")
    assert finding.status == "FIX_PROPOSED"

    h4 = await lifecycle_svc.transition_status(finding, "UNDER_REVIEW")
    assert finding.status == "UNDER_REVIEW"

    h5 = await lifecycle_svc.transition_status(finding, "FIXED")
    assert finding.status == "FIXED"
    assert finding.fixed_at is not None

    # 2. Invalid transition: FIXED directly to CONFIRMED raises ValidationError
    from backend.app.core.exceptions import ValidationError
    with pytest.raises(ValidationError):
        await lifecycle_svc.transition_status(finding, "CONFIRMED")


# ── Test 6: Finding REST APIs & Tenant Scoping ───────────────


@pytest.mark.asyncio
async def test_finding_rest_apis_and_tenant_isolation(
    client: AsyncClient, db_session: AsyncSession
):
    """Verify tenant isolation on finding listing, detail, comments, and suppression."""
    # Org A (Tenant A)
    org_a = Organization(id=uuid.uuid4(), name="Tenant A", slug="tenant-a")
    user_a = User(id=uuid.uuid4(), name="Alice Analyst", email="alice@tenanta.com", password_hash="hash", status="active")
    db_session.add_all([org_a, user_a])
    await db_session.flush()

    role_res = await db_session.execute(select(Role).where(Role.name == "security_analyst"))
    analyst_role = role_res.scalar_one()

    mem_a = OrganizationMember(
        id=uuid.uuid4(),
        organization_id=org_a.id,
        user_id=user_a.id,
        role_id=analyst_role.id,
        status="active",
    )
    project_a = Project(id=uuid.uuid4(), name="Project A", organization_id=org_a.id, owner_id=user_a.id)
    db_session.add_all([mem_a, project_a])

    # Finding in Tenant A
    finding_a = Finding(
        id=uuid.uuid4(),
        project_id=project_a.id,
        organization_id=org_a.id,
        title="Tenant A Issue",
        vulnerability_type="Injection",
        cwe_id="CWE-89",
        severity="critical",
        confidence=0.90,
        risk_score=9.0,
        status="OPEN",
        fingerprint="fp_tenant_a",
        first_seen_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
    )
    db_session.add(finding_a)

    # Org B (Tenant B)
    org_b = Organization(id=uuid.uuid4(), name="Tenant B", slug="tenant-b")
    user_b = User(id=uuid.uuid4(), name="Bob Analyst", email="bob@tenantb.com", password_hash="hash", status="active")
    db_session.add_all([org_b, user_b])
    await db_session.flush()

    mem_b = OrganizationMember(
        id=uuid.uuid4(),
        organization_id=org_b.id,
        user_id=user_b.id,
        role_id=analyst_role.id,
        status="active",
    )
    db_session.add(mem_b)
    await db_session.commit()

    token_a = create_token_pair(str(user_a.id), user_a.email)["access_token"]
    token_b = create_token_pair(str(user_b.id), user_b.email)["access_token"]

    headers_a = {"Authorization": f"Bearer {token_a}", "X-Organization-ID": str(org_a.id)}
    headers_b = {"Authorization": f"Bearer {token_b}", "X-Organization-ID": str(org_b.id)}

    # 1. Tenant A lists findings successfully
    res_a = await client.get(f"/api/v1/projects/{project_a.id}/findings", headers=headers_a)
    assert res_a.status_code == 200
    data_a = res_a.json()["data"]
    assert data_a["total"] == 1
    assert data_a["items"][0]["id"] == str(finding_a.id)

    # 2. Tenant B attempting to access Tenant A's project findings returns 404 (IDOR prevented)
    res_b = await client.get(f"/api/v1/projects/{project_a.id}/findings", headers=headers_b)
    assert res_b.status_code == 404

    # 3. Tenant B attempting to read Tenant A's finding directly returns 404
    res_b_find = await client.get(f"/api/v1/findings/{finding_a.id}", headers=headers_b)
    assert res_b_find.status_code == 404

    # 4. Tenant A gets finding summary
    sum_res = await client.get(
        f"/api/v1/projects/{project_a.id}/findings/summary", headers=headers_a
    )
    assert sum_res.status_code == 200
    sum_data = sum_res.json()["data"]
    assert sum_data["total"] == 1
    assert sum_data["critical"] == 1

    # 5. Tenant A adds a comment
    comment_res = await client.post(
        f"/api/v1/findings/{finding_a.id}/comments",
        headers=headers_a,
        json={"content": "Investigating vulnerable sink in line 45"},
    )
    assert comment_res.status_code == 201
    assert comment_res.json()["data"]["content"] == "Investigating vulnerable sink in line 45"

    # 6. Tenant A suppresses finding
    suppress_res = await client.post(
        f"/api/v1/findings/{finding_a.id}/suppress",
        headers=headers_a,
        json={
            "suppression_type": "FALSE_POSITIVE",
            "reason": "Sanitized by custom upstream filter",
        },
    )
    assert suppress_res.status_code == 200
    assert suppress_res.json()["data"]["suppression_type"] == "FALSE_POSITIVE"

    # Verify status changed to FALSE_POSITIVE
    f_check = await client.get(f"/api/v1/findings/{finding_a.id}", headers=headers_a)
    assert f_check.json()["data"]["status"] == "FALSE_POSITIVE"


# ── Test 7: Architecture Provider Isolation Audit ────────────


def test_finding_domain_has_no_mock_dependency():
    """Verify Finding domain and correlation services do NOT import MockAIProvider."""
    import backend.app.models.finding as f_mod
    import backend.app.services.finding_service.correlation as corr_mod

    f_source = inspect.getsource(f_mod)
    corr_source = inspect.getsource(corr_mod)

    assert "MockAIProvider" not in f_source, "Finding model must not import MockAIProvider"
    assert "MockAIProvider" not in corr_source, "Correlation engine must not import MockAIProvider"


# ── Test 8: Finding Assignment and Membership Validation ─────


@pytest.mark.asyncio
async def test_finding_assignment_and_membership_validation(
    client: AsyncClient, db_session: AsyncSession
):
    """Verify finding assignment succeeds for valid member, fails for non-member."""
    org = Organization(id=uuid.uuid4(), name="Assign Org", slug="assign-org")
    owner = User(id=uuid.uuid4(), name="Org Owner", email="owner@assign.com", password_hash="hash", status="active")
    member = User(id=uuid.uuid4(), name="Org Member", email="member@assign.com", password_hash="hash", status="active")
    external_user = User(id=uuid.uuid4(), name="External User", email="ext@other.com", password_hash="hash", status="active")
    db_session.add_all([org, owner, member, external_user])
    await db_session.flush()

    role_res = await db_session.execute(select(Role).where(Role.name == "security_analyst"))
    analyst_role = role_res.scalar_one()

    mem1 = OrganizationMember(id=uuid.uuid4(), organization_id=org.id, user_id=owner.id, role_id=analyst_role.id, status="active")
    mem2 = OrganizationMember(id=uuid.uuid4(), organization_id=org.id, user_id=member.id, role_id=analyst_role.id, status="active")
    project = Project(id=uuid.uuid4(), name="Assign Project", organization_id=org.id, owner_id=owner.id)
    db_session.add_all([mem1, mem2, project])

    finding = Finding(
        id=uuid.uuid4(),
        project_id=project.id,
        organization_id=org.id,
        title="Issue to assign",
        vulnerability_type="Injection",
        cwe_id="CWE-89",
        severity="high",
        confidence=0.88,
        risk_score=8.5,
        status="OPEN",
        fingerprint="fp_assign_test",
        first_seen_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
    )
    db_session.add(finding)
    await db_session.commit()

    token = create_token_pair(str(owner.id), owner.email)["access_token"]
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": str(org.id)}

    # 1. Assigning to valid member succeeds
    assign_res = await client.post(
        f"/api/v1/findings/{finding.id}/assign",
        headers=headers,
        json={"user_id": str(member.id)},
    )
    assert assign_res.status_code == 200
    assert assign_res.json()["data"]["assigned_to_user_id"] == str(member.id)

    # 2. Assigning to external user fails (validation error)
    invalid_res = await client.post(
        f"/api/v1/findings/{finding.id}/assign",
        headers=headers,
        json={"user_id": str(external_user.id)},
    )
    assert invalid_res.status_code in [400, 422]


# ── Test 9: Source Code Context from Immutable Snapshot ──────


@pytest.mark.asyncio
async def test_finding_source_context_retrieval(
    client: AsyncClient, db_session: AsyncSession
):
    """Verify source code context is retrieved from the exact immutable snapshot artifact."""
    storage = StorageService()
    test_content = (
        "import os\n"
        "import sys\n"
        "\n"
        "def query_db(user_input):\n"
        "    query = f'SELECT * FROM users WHERE id = {user_input}'\n"
        "    return execute_query(query)\n"
    ).encode("utf-8")
    artifact_key = "test_snapshots/vulnerable_file.py"
    await storage.save_object(test_content, artifact_key)

    org = Organization(id=uuid.uuid4(), name="Source Org", slug="source-org")
    user = User(id=uuid.uuid4(), name="Source User", email="source@test.com", password_hash="hash", status="active")
    db_session.add_all([org, user])
    await db_session.flush()

    role_res = await db_session.execute(select(Role).where(Role.name == "security_analyst"))
    analyst_role = role_res.scalar_one()

    member = OrganizationMember(id=uuid.uuid4(), organization_id=org.id, user_id=user.id, role_id=analyst_role.id, status="active")
    project = Project(id=uuid.uuid4(), name="Source Project", organization_id=org.id, owner_id=user.id)
    db_session.add_all([member, project])

    snap = SourceSnapshot(
        id=uuid.uuid4(),
        project_id=project.id,
        source_type="upload_zip",
        content_hash="source_snap_hash",
        artifact_uri="snapshots/test_snap.zip",
        status="ready",
    )
    db_session.add(snap)

    source_file = SourceFile(
        id=uuid.uuid4(),
        source_snapshot_id=snap.id,
        relative_path="app/query.py",
        path_hash="query_path_hash",
        language="python",
        original_artifact_uri=artifact_key,
        line_count=6,
        content_hash="query_content_hash",
    )
    scan = Scan(
        id=uuid.uuid4(),
        project_id=project.id,
        organization_id=org.id,
        source_snapshot_id=snap.id,
        status="completed",
    )
    finding = Finding(
        id=uuid.uuid4(),
        project_id=project.id,
        organization_id=org.id,
        title="SQL Injection in query_db",
        vulnerability_type="Injection",
        cwe_id="CWE-89",
        severity="critical",
        confidence=0.95,
        risk_score=9.5,
        status="OPEN",
        fingerprint="fp_source_test",
        first_seen_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
    )
    db_session.add_all([source_file, scan, finding])
    await db_session.flush()

    occ = FindingOccurrence(
        id=uuid.uuid4(),
        finding_id=finding.id,
        scan_id=scan.id,
        source_snapshot_id=snap.id,
        file_path="app/query.py",
        function_name="query_db",
        start_line=5,
        end_line=5,
        confidence=0.95,
        severity="critical",
    )
    db_session.add(occ)
    await db_session.commit()

    token = create_token_pair(str(user.id), user.email)["access_token"]
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": str(org.id)}

    src_res = await client.get(f"/api/v1/findings/{finding.id}/source?window=5", headers=headers)
    assert src_res.status_code == 200
    src_data = src_res.json()["data"]
    assert src_data["file_path"] == "app/query.py"
    assert src_data["is_snapshot_immutable"] is True
    assert "SELECT * FROM users" in src_data["source_snippet"]

