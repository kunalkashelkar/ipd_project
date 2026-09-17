# ============================================================
# Phase 5: End-to-End Scan Pipeline & Repeated Scan Test
# ============================================================
# Proves the complete automated domain path:
# READY SourceSnapshot
#   ↓
# Scan Created
#   ↓
# Static Analysis & CPG & Taint
#   ↓
# AI_ANALYSIS (Configured Provider)
#   ↓
# Canonical AIPrediction Persisted
#   ↓
# POST_PROCESSING & Correlation
#   ↓
# Finding Created
#   ↓
# FindingOccurrence Created
#   ↓
# Scan COMPLETED
#   ↓
# Repeated Scan Deduplication Proof (1 Finding, 2 Occurrences)
#   ↓
# Results APIs & Source Context Verification
# ============================================================

from __future__ import annotations

import io
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.security import create_token_pair
from backend.app.models.ai_prediction import AIPrediction
from backend.app.models.analysis_artifact import AnalysisArtifact
from backend.app.models.finding import Finding, FindingOccurrence
from backend.app.models.organization import Organization, OrganizationMember
from backend.app.models.project import Project
from backend.app.models.rbac import Role
from backend.app.models.scan import Scan
from backend.app.models.source_snapshot import Function, SourceFile, SourceSnapshot
from backend.app.models.user import User
from backend.app.storage.service import StorageService
from backend.app.workers.scan_tasks import orchestrate_scan
from backend.tests.conftest import test_session_factory as _test_session_factory
import backend.app.workers.scan_tasks as scan_tasks_mod


@pytest.mark.asyncio
async def test_phase5_end_to_end_scan_pipeline_and_deduplication(
    client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    """Prove the complete Phase 5 domain flow from scan execution to findings and repeated-scan deduplication."""
    monkeypatch.setattr(scan_tasks_mod, "async_session_factory", _test_session_factory)
    storage = StorageService()

    # 1. Create Organization, User, and Project
    org = Organization(id=uuid.uuid4(), name="E2E Pipeline Org", slug="e2e-pipeline-org")
    user = User(
        id=uuid.uuid4(),
        name="Lead Security Analyst",
        email="analyst@pipeline.org",
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
    project = Project(
        id=uuid.uuid4(),
        name="Vulnerable Backend Project",
        organization_id=org.id,
        owner_id=user.id,
        language="python",
    )
    db_session.add_all([member, project])
    await db_session.flush()

    # 2. Prepare real source code archive and upload to storage
    py_code = (
        "import sqlite3\n"
        "\n"
        "def query_user_records(user_id: str):\n"
        "    # SQL query execution with direct user input\n"
        "    query = f'SELECT * FROM users WHERE id = {user_id}'\n"
        "    conn = sqlite3.connect('app.db')\n"
        "    cursor = conn.cursor()\n"
        "    cursor.execute(query)\n"
        "    return cursor.fetchall()\n"
    )
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("app/database.py", py_code)
    zip_bytes = zip_buf.getvalue()

    archive_key = f"snapshots/{uuid.uuid4()}/source.zip"
    await storage.save_object(zip_bytes, archive_key)

    file_artifact_key = f"snapshots/{uuid.uuid4()}/app/database.py"
    await storage.save_object(py_code.encode("utf-8"), file_artifact_key)

    # 3. Create immutable SourceSnapshot, SourceFile, and Function records
    snap = SourceSnapshot(
        id=uuid.uuid4(),
        project_id=project.id,
        source_type="upload_zip",
        content_hash="snap_hash_e2e_123",
        artifact_uri=archive_key,
        status="ready",
        file_count=1,
        total_bytes=len(zip_bytes),
        detected_languages={"python": 100.0},
        preprocessing_version="v1.0.0",
        completed_at=datetime.now(timezone.utc),
    )
    db_session.add(snap)
    await db_session.flush()

    source_file = SourceFile(
        id=uuid.uuid4(),
        source_snapshot_id=snap.id,
        relative_path="app/database.py",
        path_hash="db_py_path_hash",
        language="python",
        original_artifact_uri=file_artifact_key,
        line_count=9,
        content_hash="db_py_content_hash",
    )
    db_session.add(source_file)
    await db_session.flush()

    fn_record = Function(
        id=uuid.uuid4(),
        source_file_id=source_file.id,
        function_id="fn_query_user_records",
        name="query_user_records",
        language="python",
        start_line=3,
        end_line=9,
        signature="def query_user_records(user_id: str)",
        original_content_hash="fn_orig_hash",
        normalized_content_hash="fn_norm_hash",
        token_count=35,
    )
    db_session.add(fn_record)
    await db_session.commit()

    # 4. Create Scan 1
    scan1 = Scan(
        id=uuid.uuid4(),
        project_id=project.id,
        organization_id=org.id,
        source_snapshot_id=snap.id,
        status="queued",
        progress=5.0,
        current_stage="queued",
    )
    db_session.add(scan1)
    await db_session.commit()

    # 5. Execute Scan 1 via Celery task function directly in test event loop
    await orchestrate_scan.run(str(scan1.id))

    # Verify Scan 1 reached COMPLETED
    await db_session.refresh(scan1)
    assert scan1.status == "completed"
    assert scan1.progress == 100.0

    # Verify canonical graph artifacts exist
    artifacts_res1 = await db_session.execute(
        select(AnalysisArtifact).where(AnalysisArtifact.scan_id == scan1.id)
    )
    artifacts1 = artifacts_res1.scalars().all()
    artifact_types = {a.artifact_type for a in artifacts1}
    assert "CPG" in artifact_types
    assert "CFG" in artifact_types
    assert "AST" in artifact_types
    assert "TAINT" in artifact_types

    # Verify AIPredictions were persisted
    preds_res1 = await db_session.execute(
        select(AIPrediction).where(AIPrediction.scan_id == scan1.id)
    )
    preds1 = preds_res1.scalars().all()
    assert len(preds1) > 0
    for p in preds1:
        assert p.scan_id == scan1.id
        assert p.source_snapshot_id == snap.id
        assert p.provider == "mock"
        assert p.generated_by_ai is True
        assert p.file_path == "app/database.py"

    # Verify Finding and FindingOccurrence created
    findings_res1 = await db_session.execute(
        select(Finding).where(Finding.project_id == project.id)
    )
    findings1 = findings_res1.scalars().all()
    assert len(findings1) > 0
    initial_finding_count = len(findings1)

    f1 = findings1[0]
    assert f1.status == "OPEN"
    assert f1.cwe_id.startswith("CWE-")
    assert f1.risk_score > 0.0

    occs_res1 = await db_session.execute(
        select(FindingOccurrence).where(FindingOccurrence.scan_id == scan1.id)
    )
    occs1 = occs_res1.scalars().all()
    assert len(occs1) == initial_finding_count

    # ── 6. REPEATED SCAN DEDUPLICATION ─────────────────────────
    # Run a second scan on the exact same snapshot
    scan2 = Scan(
        id=uuid.uuid4(),
        project_id=project.id,
        organization_id=org.id,
        source_snapshot_id=snap.id,
        status="queued",
        progress=5.0,
        current_stage="queued",
    )
    db_session.add(scan2)
    await db_session.commit()

    await orchestrate_scan.run(str(scan2.id))

    await db_session.refresh(scan2)
    assert scan2.status == "completed"

    # ── Verify Deduplication Guarantees ───────────────────────
    # 1. Finding count in project MUST NOT increase (exact same findings deduplicated!)
    findings_res2 = await db_session.execute(
        select(Finding).where(Finding.project_id == project.id)
    )
    findings2 = findings_res2.scalars().all()
    assert len(findings2) == initial_finding_count, (
        f"Expected {initial_finding_count} deduplicated findings, got {len(findings2)}"
    )

    # 2. Total occurrences must be doubled (one occurrence per scan)
    all_occs_res = await db_session.execute(
        select(FindingOccurrence).join(Finding).where(Finding.project_id == project.id)
    )
    all_occs = all_occs_res.scalars().all()
    assert len(all_occs) == initial_finding_count * 2

    # ── 7. REST API Verification ──────────────────────────────
    token = create_token_pair(str(user.id), user.email)["access_token"]
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": str(org.id)}

    # List project findings
    api_list = await client.get(f"/api/v1/projects/{project.id}/findings", headers=headers)
    assert api_list.status_code == 200
    list_data = api_list.json()["data"]
    assert list_data["total"] == initial_finding_count

    # Get finding detail
    detail_res = await client.get(f"/api/v1/findings/{f1.id}", headers=headers)
    assert detail_res.status_code == 200
    detail_data = detail_res.json()["data"]
    assert detail_data["id"] == str(f1.id)
    assert len(detail_data["occurrences"]) == 2  # 2 occurrences across scan 1 & 2!

    # Get immutable source context
    src_res = await client.get(f"/api/v1/findings/{f1.id}/source", headers=headers)
    assert src_res.status_code == 200
    src_data = src_res.json()["data"]
    assert src_data["is_snapshot_immutable"] is True
    assert "query_user_records" in src_data["source_snippet"]
