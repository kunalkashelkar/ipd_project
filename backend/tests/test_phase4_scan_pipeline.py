# ============================================================
# Phase 4 Automated Test Suite — Scan Pipeline, Graph & Taint
# ============================================================

import hashlib
import json
import uuid
from pathlib import Path

import networkx as nx
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.analysis_artifact import AnalysisArtifact
from backend.app.models.organization import Organization, OrganizationMember
from backend.app.models.project import Project
from backend.app.models.scan import Scan, ScanEvent, ScanStageRun
from backend.app.models.source_snapshot import SourceSnapshot
from backend.app.models.user import User
from backend.app.services.scan_lifecycle.lifecycle_service import ScanLifecycleService
from backend.app.services.scan_lifecycle.state_machine import (
    InvalidStateTransitionError,
    ScanStage,
    ScanStateMachine,
    ScanStatus,
)
from backend.app.services.static_analysis.service import StaticAnalysisService
from backend.app.services.static_analysis.taint_pipeline import TaintPipelineService


@pytest_asyncio.fixture
async def ready_snapshot_for_scan(db_session: AsyncSession, test_user: User) -> tuple[Project, SourceSnapshot]:
    """Create an authorized project with a READY immutable SourceSnapshot."""
    stmt = select(OrganizationMember).where(OrganizationMember.user_id == test_user.id)
    res = await db_session.execute(stmt)
    member = res.scalar_one()

    project = Project(
        organization_id=member.organization_id,
        name=f"Static Target {uuid.uuid4().hex[:6]}",
        owner_id=test_user.id,
        created_by=test_user.id,
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    snapshot = SourceSnapshot(
        project_id=project.id,
        source_type="upload_zip",
        content_hash=hashlib.sha256(b"dummy_code").hexdigest(),
        artifact_uri=f"organizations/{member.organization_id}/projects/{project.id}/snapshots/snap1/archive.zip",
        status="ready",
        file_count=5,
        total_bytes=1024,
    )
    db_session.add(snapshot)
    await db_session.commit()
    await db_session.refresh(snapshot)

    return project, snapshot


# ── 1. State Machine Unit Tests ─────────────────────────────


def test_scan_state_machine_legal_and_illegal_transitions():
    """Verify state machine legal forward paths and rejection of illegal backwards jumps."""
    # Valid forward transitions
    assert ScanStateMachine.can_transition(ScanStage.CREATED, ScanStage.QUEUED)
    assert ScanStateMachine.can_transition(ScanStage.QUEUED, ScanStage.PREPARING)
    assert ScanStateMachine.can_transition(ScanStage.PREPARING, ScanStage.CHECKOUT)
    assert ScanStateMachine.can_transition(ScanStage.CHECKOUT, ScanStage.PREPROCESSING)
    assert ScanStateMachine.can_transition(ScanStage.PREPROCESSING, ScanStage.STATIC_ANALYSIS)
    assert ScanStateMachine.can_transition(ScanStage.STATIC_ANALYSIS, ScanStage.GRAPH_PROCESSING)
    assert ScanStateMachine.can_transition(ScanStage.GRAPH_PROCESSING, ScanStage.AI_ANALYSIS)
    assert ScanStateMachine.can_transition(ScanStage.AI_ANALYSIS, ScanStage.POST_PROCESSING)
    assert ScanStateMachine.can_transition(ScanStage.POST_PROCESSING, ScanStage.COMPLETED)

    # Valid cancellations and failures
    assert ScanStateMachine.can_transition(ScanStage.PREPARING, ScanStage.CANCELLED)
    assert ScanStateMachine.can_transition(ScanStage.STATIC_ANALYSIS, ScanStage.FAILED)
    assert ScanStateMachine.can_transition(ScanStage.GRAPH_PROCESSING, ScanStage.TIMED_OUT)

    # Illegal backwards / terminal jumps
    assert not ScanStateMachine.can_transition(ScanStage.COMPLETED, ScanStage.QUEUED)
    assert not ScanStateMachine.can_transition(ScanStage.CANCELLED, ScanStage.PREPARING)
    assert not ScanStateMachine.can_transition(ScanStage.CREATED, ScanStage.STATIC_ANALYSIS)

    with pytest.raises(InvalidStateTransitionError):
        ScanStateMachine.validate_transition(ScanStage.COMPLETED, ScanStage.QUEUED)


def test_scan_state_machine_progress_and_status_mapping():
    """Verify deterministic progress calculation and status mapping."""
    assert ScanStateMachine.calculate_progress(ScanStage.CREATED) == 0.0
    assert ScanStateMachine.calculate_progress(ScanStage.STATIC_ANALYSIS) == 55.0
    assert ScanStateMachine.calculate_progress(ScanStage.COMPLETED) == 100.0

    assert ScanStateMachine.stage_to_status(ScanStage.CREATED) == ScanStatus.PENDING
    assert ScanStateMachine.stage_to_status(ScanStage.STATIC_ANALYSIS) == ScanStatus.RUNNING
    assert ScanStateMachine.stage_to_status(ScanStage.COMPLETED) == ScanStatus.COMPLETED
    assert ScanStateMachine.stage_to_status(ScanStage.FAILED) == ScanStatus.FAILED


# ── 2. Lifecycle Service & Event Auditing Tests ─────────────


@pytest.mark.asyncio
async def test_scan_lifecycle_atomic_transitions_and_history(
    db_session: AsyncSession, ready_snapshot_for_scan: tuple[Project, SourceSnapshot], test_user: User
):
    """Verify ScanLifecycleService manages atomic transitions, stage duration, and event logs."""
    project, snapshot = ready_snapshot_for_scan
    lifecycle = ScanLifecycleService(db_session)

    scan = Scan(
        project_id=project.id,
        organization_id=project.organization_id,
        source_snapshot_id=snapshot.id,
        created_by=test_user.id,
        status="pending",
        progress=0.0,
        current_stage="created",
    )
    db_session.add(scan)
    await db_session.commit()
    await db_session.refresh(scan)

    # Step 1: Transition CREATED -> QUEUED
    scan = await lifecycle.transition_stage(scan.id, ScanStage.QUEUED, worker_id="worker-1")
    assert scan.status == "queued"
    assert scan.current_stage == "queued"
    assert scan.worker_id == "worker-1"

    # Step 2: Transition QUEUED -> PREPARING
    scan = await lifecycle.transition_stage(scan.id, ScanStage.PREPARING, worker_id="worker-1")
    assert scan.status == "running"
    assert scan.current_stage == "preparing"
    assert scan.started_at is not None

    # Step 3: Record Heartbeat
    await lifecycle.record_heartbeat(scan.id, worker_id="worker-1")
    await db_session.refresh(scan)
    assert scan.heartbeat_at is not None

    # Step 4: Verify stage runs and events
    stmt_runs = select(ScanStageRun).where(ScanStageRun.scan_id == scan.id)
    res_runs = await db_session.execute(stmt_runs)
    runs = res_runs.scalars().all()
    assert len(runs) >= 2

    stmt_events = select(ScanEvent).where(ScanEvent.scan_id == scan.id)
    res_events = await db_session.execute(stmt_events)
    events = res_events.scalars().all()
    assert len(events) >= 2


# ── 3. Scan API & Idempotency Tests ─────────────────────────


@pytest.mark.asyncio
async def test_scan_creation_with_idempotency_key(
    client: AsyncClient,
    ready_snapshot_for_scan: tuple[Project, SourceSnapshot],
    auth_headers: dict,
):
    """Test scan creation deduplication when identical idempotency_key is submitted."""
    project, snapshot = ready_snapshot_for_scan
    idempotency_key = f"idem-key-{uuid.uuid4().hex}"

    payload = {
        "project_id": str(project.id),
        "source_snapshot_id": str(snapshot.id),
        "idempotency_key": idempotency_key,
        "config": {"modules": ["ast", "cfg", "pdg", "cpg", "taint"]},
    }

    # First request: creates scan
    res1 = await client.post("/api/v1/scans", json=payload, headers=auth_headers)
    assert res1.status_code in {200, 201}
    scan1 = res1.json()["data"]

    # Second request with identical idempotency_key: returns existing scan
    res2 = await client.post("/api/v1/scans", json=payload, headers=auth_headers)
    assert res2.status_code in {200, 201}
    scan2 = res2.json()["data"]

    assert scan1["id"] == scan2["id"]
    assert scan1["project_id"] == scan2["project_id"]


@pytest.mark.asyncio
async def test_scan_creation_rejects_unready_snapshot(
    client: AsyncClient,
    db_session: AsyncSession,
    ready_snapshot_for_scan: tuple[Project, SourceSnapshot],
    auth_headers: dict,
):
    """Test scan creation is rejected when targeting a pending or processing snapshot."""
    project, _ = ready_snapshot_for_scan

    pending_snap = SourceSnapshot(
        project_id=project.id,
        source_type="upload_zip",
        content_hash=hashlib.sha256(b"pending").hexdigest(),
        artifact_uri="pending.zip",
        status="pending",
    )
    db_session.add(pending_snap)
    await db_session.commit()
    await db_session.refresh(pending_snap)

    payload = {
        "project_id": str(project.id),
        "source_snapshot_id": str(pending_snap.id),
    }
    response = await client.post("/api/v1/scans", json=payload, headers=auth_headers)
    assert response.status_code == 422
    assert "Only READY snapshots can be scanned" in response.json()["message"]


# ── 4. Static Analysis & Canonical Graph Generation Tests ───


def test_static_analysis_service_generates_all_canonical_graphs(tmp_path: Path):
    """Test StaticAnalysisService generates AST, CFG, PDG, CPG, and CallGraph with valid schema."""
    # Setup test source directory with sample Python and JavaScript code
    source_dir = tmp_path / "src"
    source_dir.mkdir()
    (source_dir / "calc.py").write_text(
        "def add(a, b):\n    c = a + b\n    return c\n\ndef run():\n    return add(1, 2)\n",
        encoding="utf-8",
    )
    (source_dir / "server.js").write_text(
        "function handleRequest(req, res) {\n  var query = req.query;\n  eval(query);\n}\n",
        encoding="utf-8",
    )

    workspace = tmp_path / "workspace"
    scan_id = uuid.uuid4()
    snapshot_id = uuid.uuid4()

    service = StaticAnalysisService()
    artifacts, cpg = service.analyze(
        source_dir=source_dir,
        workspace=workspace,
        scan_id=scan_id,
        snapshot_id=snapshot_id,
    )

    # Check all required canonical graph types are produced
    required_types = {"AST", "CFG", "PDG", "CPG", "CALL_GRAPH"}
    assert set(artifacts.keys()) == required_types

    for g_type, meta in artifacts.items():
        assert meta.schema_version == "1.0.0"
        if g_type == "PDG" and meta.tool_name == "native_ast_analyzer":
            assert meta.status == "unsupported"
            assert meta.metadata.get("engine_fallback") is True
        else:
            assert meta.status == "ready"
            assert meta.node_count > 0
        assert meta.edge_count >= 0
        assert meta.artifact_path.exists()

        # Validate cryptographic checksum matches file bytes exactly
        file_bytes = meta.artifact_path.read_bytes()
        expected_hash = hashlib.sha256(file_bytes).hexdigest()
        assert meta.content_hash == expected_hash

        # Validate JSON structure
        data = json.loads(file_bytes.decode("utf-8"))
        assert data["schema_version"] == "1.0.0"
        assert data["graph_type"] == g_type
        assert len(data["nodes"]) == meta.node_count
        assert len(data["edges"]) == meta.edge_count

    # Check merged CPG
    assert isinstance(cpg, nx.DiGraph)
    assert cpg.number_of_nodes() > 0


# ── 5. Taint Pipeline Evidence Layer Tests ───────────────────


def test_taint_pipeline_service_generates_static_evidence(tmp_path: Path):
    """Verify TaintPipelineService runs static taint analysis and produces evidence."""
    source_dir = tmp_path / "src"
    source_dir.mkdir()
    (source_dir / "app.py").write_text(
        "def handler(user_input):\n"
        "    query = 'SELECT * FROM users WHERE id=' + user_input\n"
        "    execute_query(query)\n",
        encoding="utf-8",
    )

    workspace = tmp_path / "workspace"
    scan_id = uuid.uuid4()
    snapshot_id = uuid.uuid4()

    static_service = StaticAnalysisService()
    artifacts, cpg = static_service.analyze(
        source_dir=source_dir,
        workspace=workspace,
        scan_id=scan_id,
        snapshot_id=snapshot_id,
    )

    taint_service = TaintPipelineService()
    taint_meta = taint_service.run_taint_analysis(
        cpg=cpg,
        workspace=workspace,
        scan_id=scan_id,
        snapshot_id=snapshot_id,
    )

    assert taint_meta.schema_version == "1.0.0"
    assert taint_meta.status == "ready"
    assert taint_meta.artifact_path.exists()

    file_bytes = taint_meta.artifact_path.read_bytes()
    expected_hash = hashlib.sha256(file_bytes).hexdigest()
    assert taint_meta.content_hash == expected_hash

    payload = json.loads(file_bytes.decode("utf-8"))
    assert payload["schema_version"] == "1.0.0"
    assert "paths" in payload
    assert "taint_rules_version" in payload


# ── 6. Scan Cancellation & Retry Tests ───────────────────────


@pytest.mark.asyncio
async def test_scan_cancellation_and_retry_api(
    client: AsyncClient,
    db_session: AsyncSession,
    ready_snapshot_for_scan: tuple[Project, SourceSnapshot],
    test_user: User,
    auth_headers: dict,
):
    """Test active scan cancellation and retry endpoints."""
    project, snapshot = ready_snapshot_for_scan
    lifecycle = ScanLifecycleService(db_session)

    scan = Scan(
        project_id=project.id,
        organization_id=project.organization_id,
        source_snapshot_id=snapshot.id,
        created_by=test_user.id,
        status="running",
        progress=55.0,
        current_stage="static_analysis",
    )
    db_session.add(scan)
    await db_session.commit()
    await db_session.refresh(scan)

    # Cancel scan
    res_cancel = await client.post(f"/api/v1/scans/{scan.id}/cancel", headers=auth_headers)
    assert res_cancel.status_code == 200

    await db_session.refresh(scan)
    assert scan.status == "cancelled"
    assert scan.cancelled_at is not None

    # Transition to failed to test retry endpoint
    scan.status = "failed"
    scan.current_stage = "failed"
    await db_session.commit()

    # Retry scan
    res_retry = await client.post(f"/api/v1/scans/{scan.id}/retry", headers=auth_headers)
    assert res_retry.status_code == 200
    retried_data = res_retry.json()["data"]
    assert retried_data["status"] in {"queued", "retrying"}
    assert retried_data["retry_count"] == 1


# ── 7. Cross-Tenant Isolation Tests ─────────────────────────


@pytest.mark.asyncio
async def test_cross_tenant_scan_isolation_blocked(
    client: AsyncClient,
    db_session: AsyncSession,
    ready_snapshot_for_scan: tuple[Project, SourceSnapshot],
    test_user: User,
):
    """Test user in Tenant A cannot read, cancel, or access artifacts of Tenant B scans."""
    from backend.app.core.security import hash_password

    project_b, snapshot_b = ready_snapshot_for_scan

    # Create Tenant A user
    org_a = Organization(name="Tenant A Org", slug=f"tenant-a-{uuid.uuid4().hex[:6]}")
    user_a = User(
        name="Tenant A User",
        email=f"user_a_{uuid.uuid4().hex[:6]}@example.com",
        password_hash=hash_password("password123"),
        role="researcher",
        status="active",
        is_verified=True,
    )
    db_session.add_all([org_a, user_a])
    await db_session.commit()
    await db_session.refresh(org_a)
    await db_session.refresh(user_a)

    from backend.app.models.rbac import Role

    stmt_role = select(Role).where(Role.name == "owner")
    res_role = await db_session.execute(stmt_role)
    owner_role = res_role.scalar_one()

    member_a = OrganizationMember(organization_id=org_a.id, user_id=user_a.id, role_id=owner_role.id, status="active")
    db_session.add(member_a)
    await db_session.commit()

    from backend.app.core.security import create_token_pair

    tokens_a = create_token_pair(str(user_a.id), user_a.email)
    headers_a = {"Authorization": f"Bearer {tokens_a['access_token']}"}

    # Create scan in Tenant B
    scan_b = Scan(
        project_id=project_b.id,
        organization_id=project_b.organization_id,
        source_snapshot_id=snapshot_b.id,
        created_by=test_user.id,
        status="running",
        current_stage="static_analysis",
    )
    db_session.add(scan_b)
    await db_session.commit()
    await db_session.refresh(scan_b)

    # Tenant A attempts to view scan B -> 403 / 404
    res_get = await client.get(f"/api/v1/scans/{scan_b.id}", headers=headers_a)
    assert res_get.status_code in {403, 404}

    # Tenant A attempts to cancel scan B -> 403 / 404
    res_cancel = await client.post(f"/api/v1/scans/{scan_b.id}/cancel", headers=headers_a)
    assert res_cancel.status_code in {403, 404}

    # Tenant A attempts to view artifacts of scan B -> 403 / 404
    res_artifacts = await client.get(f"/api/v1/scans/{scan_b.id}/artifacts", headers=headers_a)
    assert res_artifacts.status_code in {403, 404}
