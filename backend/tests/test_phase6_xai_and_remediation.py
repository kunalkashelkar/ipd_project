# ============================================================
# Phase 6: XAI, Remediation, Sandbox Validation & Verification Tests
# ============================================================
# Comprehensive automated test suite for:
# - Model Registry & LocalTorchProvider error boundaries
# - Patch security, directory traversal defense & isolated workspace apply
# - Evidence-aware XAI explanations & truthful unsupported statuses
# - Remediation generation, human review lifecycle & superseding
# - Multi-stage isolated validation (Syntax, Build, Tests, Static, Taint)
# - Authoritative finding verification & regression/reopen behavior
# - Tenant isolation and RBAC permission enforcement
# ============================================================

from __future__ import annotations

import os
import shutil
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.security import create_token_pair
from backend.app.models.ai_prediction import AIPrediction
from backend.app.models.finding import (
    Finding,
    FindingOccurrence,
    FindingStatusHistory,
)
from backend.app.models.model_registry import ModelVersion
from backend.app.models.organization import Organization, OrganizationMember
from backend.app.models.project import Project
from backend.app.models.rbac import Permission, Role, RolePermission
from backend.app.models.remediation import Remediation, RemediationValidation
from backend.app.models.scan import Scan
from backend.app.models.source_snapshot import SourceFile, SourceSnapshot
from backend.app.models.user import User
from backend.app.services.ai_inference import get_ai_provider
from backend.app.services.ai_inference.contracts import (
    AIErrorCode,
    AIInferenceError,
    CanonicalAIPrediction,
    CanonicalAIRequest,
)

from backend.app.services.ai_inference.local_torch_provider import LocalTorchProvider
from backend.app.services.finding_service.correlation import FindingCorrelationService
from backend.app.services.finding_service.fingerprint import compute_finding_fingerprint
from backend.app.services.finding_service.lifecycle import FindingLifecycleService
from backend.app.services.model_registry.service import ModelRegistryService
from backend.app.services.remediation.patch_service import PatchSecurityError, PatchService
from backend.app.services.remediation.provider import (
    DevelopmentRemediationProvider,
    get_remediation_provider,
)
from backend.app.services.remediation.service import RemediationService
from backend.app.services.remediation.validation_service import ValidationService
from backend.app.services.xai.service import XAIExplanationService
from backend.app.storage.service import StorageService


async def create_phase6_context(db_session: AsyncSession) -> dict:
    """Helper to seed test user, tenant organization, project, snapshot, and finding."""
    user = User(
        id=uuid.uuid4(),
        email=f"security-analyst-{uuid.uuid4().hex[:6]}@example.com",
        password_hash="fake_hash",
        name="Security Analyst",
        status="active",
    )

    db_session.add(user)

    org = Organization(
        id=uuid.uuid4(),
        name=f"SecCorp-{uuid.uuid4().hex[:6]}",
        slug=f"seccorp-{uuid.uuid4().hex[:6]}",
        is_active=True,
    )
    db_session.add(org)

    stmt = select(Role).where(Role.name == "owner")
    res = await db_session.execute(stmt)
    role = res.scalar_one()


    member = OrganizationMember(
        id=uuid.uuid4(),
        organization_id=org.id,
        user_id=user.id,
        role_id=role.id,
        status="active",
    )
    db_session.add(member)

    project = Project(
        id=uuid.uuid4(),
        organization_id=org.id,
        name=f"Vulnerable Service-{uuid.uuid4().hex[:6]}",
        owner_id=user.id,
        language="python",
    )
    db_session.add(project)



    snapshot = SourceSnapshot(
        id=uuid.uuid4(),
        project_id=project.id,
        source_type="upload_zip",
        source_version="v1.0",
        content_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        artifact_uri="s3://snapshots/test.zip",
        status="ready",
        file_count=2,
        total_bytes=1024,
    )
    db_session.add(snapshot)

    scan = Scan(
        id=uuid.uuid4(),
        project_id=project.id,
        organization_id=org.id,
        source_snapshot_id=snapshot.id,
        status="completed",
        progress=100.0,
    )
    db_session.add(scan)


    finding = Finding(
        id=uuid.uuid4(),
        project_id=project.id,
        organization_id=org.id,
        title="SQL Injection in user search",
        vulnerability_type="SQL Injection",
        cwe_id="CWE-89",
        severity="critical",
        cvss_score=9.8,
        confidence=0.95,
        risk_score=9.6,
        status="IN_PROGRESS",
        fingerprint=f"fp-sqli-{uuid.uuid4().hex[:8]}",
        first_seen_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
    )
    db_session.add(finding)

    occ = FindingOccurrence(
        id=uuid.uuid4(),
        finding_id=finding.id,
        scan_id=scan.id,
        source_snapshot_id=snapshot.id,
        file_path="app/views.py",
        function_name="search_users",
        start_line=42,
        end_line=45,
        confidence=0.95,
        severity="critical",
        observed_at=datetime.now(timezone.utc),
    )
    db_session.add(occ)

    await db_session.commit()

    return {
        "user": user,
        "org": org,
        "project": project,
        "snapshot": snapshot,
        "scan": scan,
        "finding": finding,
        "occurrence": occ,
    }


# ── Test 1: Model Registry Functionality ─────────────────────

@pytest.mark.asyncio
async def test_model_registry_crud(db_session: AsyncSession):
    """Test model registration, activation, deactivation, and checksum tracking."""
    service = ModelRegistryService(db_session)
    model_name = f"VulnerabilityGAT-{uuid.uuid4().hex[:4]}"
    version = "v1.2.0"

    # Register new model version
    mv = await service.register_model(
        model_name=model_name,
        version=version,
        provider="local_torch",
        artifact_uri="s3://models/gat-v1.2.0.pt",
        checksum="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        runtime="pytorch",
        input_schema_version="v1.0.0",
        output_schema_version="v1.0.0",
        metadata={"architecture": "GAT", "num_layers": 4},
    )
    assert mv.id is not None
    assert mv.model_name == model_name
    assert mv.status == "inactive"
    assert mv.activated_at is None

    # Activate model version
    activated = await service.activate_model(mv.id)
    assert activated.status == "active"
    assert activated.activated_at is not None

    # Deactivate model version
    deactivated = await service.deactivate_model(mv.id)
    assert deactivated.status == "inactive"

    # Listing models
    models = await service.list_models()
    assert any(m.id == mv.id for m in models)


# ── Test 2: LocalTorchProvider Boundary & Error States ───────

@pytest.mark.asyncio
async def test_local_torch_provider_boundary():
    """Verify LocalTorchProvider reports structured MODEL_NOT_READY when weights are missing."""
    provider = LocalTorchProvider(checkpoint_path="non_existent_weights.pt")
    assert provider.provider_id == "local_torch"

    meta = provider.get_metadata()
    assert meta["checkpoint_exists"] is False
    assert meta["runtime"] == "pytorch"

    req = CanonicalAIRequest(
        scan_id=uuid.uuid4(),
        source_snapshot_id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        language="python",
    )

    with pytest.raises(AIInferenceError) as exc_info:
        await provider.predict(req)
    assert "MODEL_NOT_READY" in str(exc_info.value.code) or "PROVIDER_UNAVAILABLE" in str(exc_info.value.code)


# ── Test 3: Patch Security & Path Traversal Rejection ─────────

def test_patch_security_sanitization():
    """Verify PatchService rejects directory traversal, absolute paths, and malformed diffs."""
    # 1. Reject empty diff
    with pytest.raises(PatchSecurityError) as exc:
        PatchService.validate_patch_security("")
    assert "empty" in str(exc.value).lower()

    # 2. Reject absolute paths
    abs_diff = """--- a//etc/shadow\n+++ b//etc/shadow\n@@ -1,1 +1,1 @@\n-root:x:\n+root:pwned:"""
    with pytest.raises(PatchSecurityError) as exc:
        PatchService.validate_patch_security(abs_diff)
    assert "absolute path" in str(exc.value).lower() or "root" in str(exc.value).lower()

    # 3. Reject directory traversal
    traversal_diff = """--- a/../../etc/passwd\n+++ b/../../etc/passwd\n@@ -1,1 +1,1 @@\n-test\n+hacked"""
    with pytest.raises(PatchSecurityError) as exc:
        PatchService.validate_patch_security(traversal_diff)
    assert "directory traversal" in str(exc.value).lower()

    # 4. Valid relative diff passes
    valid_diff = """--- a/app/views.py\n+++ b/app/views.py\n@@ -42,3 +42,3 @@\n-query = f"SELECT * FROM users WHERE id = '{uid}'"\n+cursor.execute("SELECT * FROM users WHERE id = %s", (uid,))"""
    changed = PatchService.validate_patch_security(valid_diff)
    assert changed == ["app/views.py"]


# ── Test 4: Isolated Workspace Patch Application ─────────────

def test_isolated_workspace_patch_application():
    """Verify patches apply to clean isolated target workspace without modifying base files."""
    with tempfile.TemporaryDirectory() as src_dir, tempfile.TemporaryDirectory() as dst_dir:
        src_path = Path(src_dir)
        dst_path = Path(dst_dir)

        # Create original source file
        vulnerable_file = src_path / "app" / "views.py"
        vulnerable_file.parent.mkdir(parents=True, exist_ok=True)
        vulnerable_file.write_text(
            'def search_users(req):\n    query = f"SELECT * FROM users WHERE id = \'{uid}\'"\n    return db.execute(query)\n'
        )

        valid_diff = (
            "--- a/app/views.py\n"
            "+++ b/app/views.py\n"
            "@@ -1,3 +1,3 @@\n"
            " def search_users(req):\n"
            '-    query = f"SELECT * FROM users WHERE id = \'{uid}\'"\n'
            '+    return db.execute("SELECT * FROM users WHERE id = %s", (uid,))\n'
            "     return db.execute(query)\n"
        )

        res = PatchService.apply_patch_to_workspace(
            source_workspace=src_path,
            patch_content=valid_diff,
            target_workspace=dst_path,
        )

        assert res["status"] == "PASS"

        # Check target workspace has patched content
        patched_file = dst_path / "app" / "views.py"
        assert patched_file.exists()
        patched_content = patched_file.read_text()
        assert "SELECT * FROM users WHERE id = %s" in patched_content

        # Verify base workspace is completely untouched
        original_content = vulnerable_file.read_text()
        assert 'query = f"SELECT * FROM users WHERE id = \'{uid}\'"' in original_content


# ── Test 5: Remediation Generation & History ──────────────────

@pytest.mark.asyncio
async def test_remediation_generation_and_consecutive_numbers(db_session: AsyncSession):
    """Test remediation generation, provenance, and consecutive numbering."""
    ctx = await create_phase6_context(db_session)
    finding = ctx["finding"]
    org = ctx["org"]
    user = ctx["user"]

    service = RemediationService(db_session)

    # Generate first remediation
    rem1 = await service.generate_remediation(
        finding_id=finding.id,
        organization_id=org.id,
        user_id=user.id,
    )
    assert rem1.id is not None
    assert rem1.remediation_number == 1
    assert rem1.status == "GENERATED"
    assert rem1.is_active_candidate is True
    assert rem1.patch_checksum is not None
    assert len(rem1.patch_checksum) == 64  # SHA-256

    # Generate second remediation
    rem2 = await service.generate_remediation(
        finding_id=finding.id,
        organization_id=org.id,
        user_id=user.id,
    )
    assert rem2.remediation_number == 2
    assert rem2.is_active_candidate is True

    # rem1 should now be inactive candidate
    await db_session.refresh(rem1)
    assert rem1.is_active_candidate is False


# ── Test 6: Human Review Lifecycle (Approve / Reject) ─────────

@pytest.mark.asyncio
async def test_remediation_human_review(db_session: AsyncSession):
    """Test human review: APPROVE and REJECT transitions and rejection guards."""
    ctx = await create_phase6_context(db_session)
    service = RemediationService(db_session)

    rem = await service.generate_remediation(
        finding_id=ctx["finding"].id,
        organization_id=ctx["org"].id,
        user_id=ctx["user"].id,
    )

    # Approve
    approved = await service.review_remediation(
        remediation_id=rem.id,
        organization_id=ctx["org"].id,
        user_id=ctx["user"].id,
        decision="APPROVE",
        comment="LGTM, patch uses parameterized query",
    )
    assert approved.status == "APPROVED"
    assert approved.reviewed_at is not None
    assert approved.review_comment == "LGTM, patch uses parameterized query"

    # Reject another remediation
    rem_reject = await service.generate_remediation(
        finding_id=ctx["finding"].id,
        organization_id=ctx["org"].id,
        user_id=ctx["user"].id,
    )
    rejected = await service.review_remediation(
        remediation_id=rem_reject.id,
        organization_id=ctx["org"].id,
        user_id=ctx["user"].id,
        decision="REJECT",
        comment="Introduces syntax error",
    )
    assert rejected.status == "REJECTED"

    # Cannot apply or validate rejected remediation
    from backend.app.core.exceptions import ValidationError
    with pytest.raises(ValidationError):
        await service.apply_remediation(
            remediation_id=rejected.id,
            organization_id=ctx["org"].id,
            user_id=ctx["user"].id,
        )


# ── Test 7: Evidence-Aware XAI & Attribution ─────────────────

@pytest.mark.asyncio
async def test_xai_explanation_generation_and_unsupported_states(db_session: AsyncSession):
    """Test XAI explanation generation and truthful unsupported method status."""
    ctx = await create_phase6_context(db_session)
    xai = XAIExplanationService(db_session)

    # 1. Evidence-aware synthesizer generates valid explanation
    exp = await xai.generate_explanation(
        finding_id=ctx["finding"].id,
        organization_id=ctx["org"].id,
        user_id=ctx["user"].id,
        method="evidence_synthesizer",
    )
    assert exp.id is not None
    assert exp.explanation_method == "evidence_synthesizer"
    assert exp.method_status in ("COMPLETED", "SUPPORTED")
    assert "CWE-89" in exp.summary
    assert len(exp.important_locations) > 0

    # 2. Integrated Gradients without PyTorch checkpoint returns MODEL_NOT_READY (no fake values)
    exp_ig = await xai.generate_explanation(
        finding_id=ctx["finding"].id,
        organization_id=ctx["org"].id,
        user_id=ctx["user"].id,
        method="integrated_gradients",
    )
    assert exp_ig.explanation_method == "integrated_gradients"
    assert exp_ig.method_status in ("MODEL_NOT_READY", "NOT_SUPPORTED")
    assert exp_ig.status_reason is not None

    # 3. GNNExplainer without compatible graph model returns NOT_SUPPORTED
    exp_gnn = await xai.generate_explanation(
        finding_id=ctx["finding"].id,
        organization_id=ctx["org"].id,
        user_id=ctx["user"].id,
        method="gnn_explainer",
    )
    assert exp_gnn.explanation_method == "gnn_explainer"
    assert exp_gnn.method_status in ("MODEL_NOT_READY", "NOT_SUPPORTED")


# ── Test 8: Multi-Stage Validation & Verification Decision ───

@pytest.mark.asyncio
async def test_multi_stage_validation_and_authoritative_verification(db_session: AsyncSession):
    """Test multi-stage validation and authoritative transition to FIXED and VERIFIED."""
    ctx = await create_phase6_context(db_session)
    finding = ctx["finding"]
    org = ctx["org"]
    user = ctx["user"]

    rem_service = RemediationService(db_session)

    rem = await rem_service.generate_remediation(
        finding_id=finding.id,
        organization_id=org.id,
        user_id=user.id,
    )

    # Execute isolated validation
    val = await rem_service.validate_remediation(
        remediation_id=rem.id,
        organization_id=org.id,
        user_id=user.id,
        run_tests=False,
    )

    assert val.status == "PASSED"
    assert val.patch_apply_result.get("status") == "PASS"
    assert val.syntax_result.get("status") == "PASS"
    assert val.final_verification_result == "VERIFIED"
    assert val.verification_scan_id is not None

    # Verify finding transitioned to VERIFIED via authoritative lifecycle
    await db_session.refresh(finding)
    assert finding.status == "VERIFIED"
    assert finding.fixed_at is not None

    # Verify verification status query returns complete evidence chain
    v_status = await rem_service.get_verification_status(finding.id, org.id)
    assert v_status["is_verified"] is True
    assert v_status["finding_status"] == "VERIFIED"
    assert v_status["verification_scan_id"] == val.verification_scan_id


# ── Test 9: Regression & Reopen Behavior ──────────────────────

@pytest.mark.asyncio
async def test_regression_reopens_verified_finding(db_session: AsyncSession):
    """Test that subsequent detection reopens a VERIFIED finding and records historical state."""
    ctx = await create_phase6_context(db_session)
    finding = ctx["finding"]
    finding.status = "VERIFIED"
    finding.fixed_at = datetime.now(timezone.utc)

    # Compute stable fingerprint matching the simulated subsequent prediction
    fp, _ = compute_finding_fingerprint(
        cwe_id="CWE-89",
        file_path="app/views.py",
        function_name="search_users",
        line_number=42,
        evidence={"vulnerability_type": "SQL Injection"},
    )
    finding.fingerprint = fp
    await db_session.commit()

    # Simulate subsequent scan detecting the exact same vulnerability fingerprint
    ai_pred = AIPrediction(
        id=uuid.uuid4(),
        scan_id=ctx["scan"].id,
        source_snapshot_id=ctx["snapshot"].id,
        file_path="app/views.py",
        function_name="search_users",
        line_number=42,
        prediction="VULNERABLE",
        confidence=0.98,
        severity="critical",
        cwe_id="CWE-89",
        cvss_score=9.8,
        provider="mock",
        model_name="MockAIProvider",
        model_version="v1.0.0",
        evidence_json={"vulnerability_type": "SQL Injection"},
    )
    db_session.add(ai_pred)
    await db_session.commit()

    correlation = FindingCorrelationService(db_session)
    correlated = await correlation.correlate_and_persist(
        scan=ctx["scan"],
        snapshot=ctx["snapshot"],
        ai_predictions=[ai_pred],
    )
    await db_session.commit()

    # Finding should be deduplicated to the existing finding
    assert len(correlated) == 1
    assert correlated[0].id == finding.id

    # Finding status must now be REOPENED
    await db_session.refresh(finding)
    assert finding.status == "REOPENED"

    # Status history should record previous_status as VERIFIED
    hist_stmt = (
        select(FindingStatusHistory)
        .where(FindingStatusHistory.finding_id == finding.id)
        .order_by(FindingStatusHistory.created_at.desc())
    )
    hist_res = await db_session.execute(hist_stmt)
    history = hist_res.scalars().first()
    assert history is not None
    assert history.previous_status == "VERIFIED"
    assert history.new_status == "REOPENED"


# ── Test 10: Multi-Tenancy Isolation & RBAC ───────────────────

@pytest.mark.asyncio
async def test_multi_tenant_remediation_isolation(db_session: AsyncSession):
    """Test that Organization B cannot view or manipulate Organization A's remediations."""
    ctx = await create_phase6_context(db_session)
    rem_service = RemediationService(db_session)

    rem = await rem_service.generate_remediation(
        finding_id=ctx["finding"].id,
        organization_id=ctx["org"].id,
        user_id=ctx["user"].id,
    )

    # Create distinct foreign Organization B
    foreign_org = Organization(
        id=uuid.uuid4(),
        name=f"Foreign Corp-{uuid.uuid4().hex[:6]}",
        slug=f"foreign-corp-{uuid.uuid4().hex[:6]}",
        is_active=True,
    )
    db_session.add(foreign_org)
    await db_session.commit()

    # Attempting to access remediation with foreign org_id must fail with NotFoundError
    from backend.app.core.exceptions import NotFoundError
    with pytest.raises(NotFoundError):
        await rem_service.review_remediation(
            remediation_id=rem.id,
            organization_id=foreign_org.id,
            user_id=ctx["user"].id,
            decision="APPROVE",
        )

    with pytest.raises(NotFoundError):
        await rem_service.get_verification_status(
            finding_id=ctx["finding"].id,
            organization_id=foreign_org.id,
        )
