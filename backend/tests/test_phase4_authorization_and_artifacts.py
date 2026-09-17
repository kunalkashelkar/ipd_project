# ============================================================
# Phase 4 Final Repair — Authorization, Tenant Isolation & Artifact Download Tests
# ============================================================

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.security import create_token_pair, hash_password
from backend.app.database.base import Base
from backend.app.database.session import get_db
from backend.app.main import app
from backend.app.models.analysis_artifact import AnalysisArtifact
from backend.app.models.organization import Organization, OrganizationMember
from backend.app.models.project import Project
from backend.app.models.rbac import Role
from backend.app.models.scan import Scan
from backend.app.models.source_snapshot import SourceSnapshot
from backend.app.models.user import User
from backend.app.services.static_analysis.service import StaticAnalysisService
from backend.app.storage.service import StorageService


# ── Helpers & Fixtures ─────────────────────────────────────────


async def create_tenant_environment(db_session: AsyncSession, name_prefix: str):
    """Create an organization with project, snapshot, scan, and canonical artifacts."""
    org = Organization(
        id=uuid.uuid4(),
        name=f"{name_prefix} Org",
        slug=f"{name_prefix.lower()}-org-{uuid.uuid4().hex[:6]}",
        is_active=True,
    )
    db_session.add(org)
    await db_session.flush()

    # Create users with each of the 5 canonical roles in this org
    role_names = ["owner", "admin", "security_analyst", "developer", "viewer"]
    roles = {}
    for rname in role_names:
        stmt = select(Role).where(Role.name == rname)
        roles[rname] = (await db_session.execute(stmt)).scalar_one()

    users = {}
    headers = {}
    for rname in role_names:
        u = User(
            id=uuid.uuid4(),
            name=f"{name_prefix} {rname.title()}",
            email=f"{rname}@{name_prefix.lower()}.local",
            password_hash=hash_password("Password123!"),
            role="member",
            status="active",
            is_verified=True,
        )
        db_session.add(u)
        await db_session.flush()

        member = OrganizationMember(
            id=uuid.uuid4(),
            organization_id=org.id,
            user_id=u.id,
            role_id=roles[rname].id,
            status="active",
        )
        db_session.add(member)
        users[rname] = u

        tokens = create_token_pair(str(u.id), u.email)
        headers[rname] = {
            "Authorization": f"Bearer {tokens['access_token']}",
            "X-Organization-ID": str(org.id),
        }

    # Project
    project = Project(
        id=uuid.uuid4(),
        organization_id=org.id,
        name=f"{name_prefix} Security Repo",
        language="Python",
        owner_id=users["owner"].id,
    )
    db_session.add(project)
    await db_session.flush()

    # Snapshot
    snapshot = SourceSnapshot(
        id=uuid.uuid4(),
        project_id=project.id,
        source_type="upload_zip",
        source_version="1.0.0",
        content_hash="a" * 64,
        artifact_uri=f"organizations/{org.id}/projects/{project.id}/snapshots/archive.zip",
        status="ready",
        file_count=1,
        total_bytes=1024,
    )
    db_session.add(snapshot)
    await db_session.flush()

    # Scan
    scan = Scan(
        id=uuid.uuid4(),
        project_id=project.id,
        organization_id=org.id,
        source_snapshot_id=snapshot.id,
        created_by=users["developer"].id,
        status="completed",
        progress=100.0,
        current_stage="completed",
    )
    db_session.add(scan)
    await db_session.flush()

    # Artifacts: 5 Canonical Graphs + 1 TAINT
    storage = StorageService()
    graph_types = ["AST", "CFG", "PDG", "CPG", "CALL_GRAPH", "TAINT"]
    artifacts = {}

    for g_type in graph_types:
        art_id = uuid.uuid4()
        storage_key = StorageService.scan_artifact_key(
            org_id=org.id,
            project_id=project.id,
            scan_id=scan.id,
            artifact_type=g_type,
            artifact_id=art_id,
        )
        sample_data = {
            "schema_version": "1.0.0",
            "artifact_id": str(art_id),
            "scan_id": str(scan.id),
            "graph_type": g_type,
            "nodes": [{"id": f"{g_type}_node_1"}],
            "edges": [],
        }
        json_bytes = json.dumps(sample_data).encode("utf-8")
        await storage.save_object(json_bytes, storage_key)

        art = AnalysisArtifact(
            id=art_id,
            scan_id=scan.id,
            source_snapshot_id=snapshot.id,
            artifact_type=g_type,
            schema_version="1.0.0",
            artifact_uri=storage_key,
            content_hash="d" * 64,
            size_bytes=len(json_bytes),
            status="unsupported" if g_type == "PDG" else "ready",
            tool_name="native_ast_analyzer",
            tool_version="1.0.0",
            node_count=1,
            edge_count=0,
            artifact_metadata={"engine_fallback": True} if g_type == "PDG" else {},
        )
        db_session.add(art)
        artifacts[g_type] = art

    await db_session.commit()

    return {
        "org": org,
        "users": users,
        "headers": headers,
        "project": project,
        "snapshot": snapshot,
        "scan": scan,
        "artifacts": artifacts,
    }


# ── 1. Scans Listing Authorization (All 5 Roles) ───────────────


@pytest.mark.asyncio
async def test_all_five_roles_can_list_scans_without_admin_gate(
    client: AsyncClient, db_session: AsyncSession
):
    """OWNER, ADMIN, SECURITY_ANALYST, DEVELOPER, and VIEWER can all list scans via scan.read."""
    tenant = await create_tenant_environment(db_session, "Alpha")

    for role_name in ["owner", "admin", "security_analyst", "developer", "viewer"]:
        resp = await client.get("/api/v1/scans", headers=tenant["headers"][role_name])
        assert resp.status_code == 200, f"Role {role_name} failed to list scans: {resp.text}"
        data = resp.json()["data"]
        items = data["items"]
        assert len(items) >= 1
        assert any(item["id"] == str(tenant["scan"].id) for item in items)


@pytest.mark.asyncio
async def test_all_five_roles_can_read_project(
    client: AsyncClient, db_session: AsyncSession
):
    """All 5 roles possess project.read and can retrieve projects."""
    tenant = await create_tenant_environment(db_session, "Beta")
    proj_id = str(tenant["project"].id)

    for role_name in ["owner", "admin", "security_analyst", "developer", "viewer"]:
        # List projects
        list_resp = await client.get("/api/v1/projects", headers=tenant["headers"][role_name])
        assert list_resp.status_code == 200, f"Role {role_name} failed project list"

        # Get specific project
        detail_resp = await client.get(f"/api/v1/projects/{proj_id}", headers=tenant["headers"][role_name])
        assert detail_resp.status_code == 200, f"Role {role_name} failed project detail"
        assert detail_resp.json()["data"]["id"] == proj_id


# ── 2. Cross-Tenant Isolation ─────────────────────────────────


@pytest.mark.asyncio
async def test_cross_tenant_scan_listing_isolation(
    client: AsyncClient, db_session: AsyncSession
):
    """Users in Tenant A cannot see Tenant B's scans, even if they have scan.read."""
    tenant_a = await create_tenant_environment(db_session, "TenantA")
    tenant_b = await create_tenant_environment(db_session, "TenantB")

    # Tenant A user lists scans
    resp_a = await client.get("/api/v1/scans", headers=tenant_a["headers"]["developer"])
    assert resp_a.status_code == 200
    ids_a = [s["id"] for s in resp_a.json()["data"]["items"]]
    assert str(tenant_a["scan"].id) in ids_a
    assert str(tenant_b["scan"].id) not in ids_a

    # Tenant B user lists scans
    resp_b = await client.get("/api/v1/scans", headers=tenant_b["headers"]["developer"])
    assert resp_b.status_code == 200
    ids_b = [s["id"] for s in resp_b.json()["data"]["items"]]
    assert str(tenant_b["scan"].id) in ids_b
    assert str(tenant_a["scan"].id) not in ids_b


@pytest.mark.asyncio
async def test_cross_tenant_scan_detail_returns_404(
    client: AsyncClient, db_session: AsyncSession
):
    """Knowing another tenant's scan UUID returns 404 to avoid leaking existence."""
    tenant_a = await create_tenant_environment(db_session, "TenantA")
    tenant_b = await create_tenant_environment(db_session, "TenantB")

    foreign_scan_id = str(tenant_b["scan"].id)
    headers_a = tenant_a["headers"]["owner"]

    for sub_path in ["", "/status", "/stages", "/artifacts", "/taint-evidence"]:
        resp = await client.get(f"/api/v1/scans/{foreign_scan_id}{sub_path}", headers=headers_a)
        assert resp.status_code == 404, f"Path /scans/{foreign_scan_id}{sub_path} leaked cross-tenant"


@pytest.mark.asyncio
async def test_cross_tenant_project_detail_returns_404(
    client: AsyncClient, db_session: AsyncSession
):
    """Knowing another tenant's project UUID returns 404."""
    tenant_a = await create_tenant_environment(db_session, "TenantA")
    tenant_b = await create_tenant_environment(db_session, "TenantB")

    resp = await client.get(
        f"/api/v1/projects/{tenant_b['project'].id}",
        headers=tenant_a["headers"]["owner"],
    )
    assert resp.status_code == 404


# ── 3. Membership Validation ──────────────────────────────────


@pytest.mark.asyncio
async def test_suspended_or_removed_member_is_denied(
    client: AsyncClient, db_session: AsyncSession
):
    """Suspended or inactive members cannot access organization scans or projects."""
    tenant = await create_tenant_environment(db_session, "Gamma")

    # Suspend viewer
    stmt = (
        select(OrganizationMember)
        .where(
            OrganizationMember.organization_id == tenant["org"].id,
            OrganizationMember.user_id == tenant["users"]["viewer"].id,
        )
    )
    member = (await db_session.execute(stmt)).scalar_one()
    member.status = "suspended"
    await db_session.commit()

    resp = await client.get("/api/v1/scans", headers=tenant["headers"]["viewer"])
    assert resp.status_code == 403


# ── 4. Artifact Download Security & Correctness ───────────────


@pytest.mark.asyncio
async def test_authorized_user_can_download_canonical_artifact(
    client: AsyncClient, db_session: AsyncSession
):
    """Authorized tenant member can download canonical JSON artifact directly."""
    tenant = await create_tenant_environment(db_session, "DownloadTest")
    scan_id = str(tenant["scan"].id)
    art_ast = tenant["artifacts"]["AST"]

    resp = await client.get(
        f"/api/v1/scans/{scan_id}/artifacts/{art_ast.id}/download",
        headers=tenant["headers"]["developer"],
    )
    assert resp.status_code == 200

    # Verify content type and content disposition
    assert resp.headers["content-type"].startswith("application/json")
    expected_filename = f"ast-{scan_id}.json"
    assert f'filename="{expected_filename}"' in resp.headers["content-disposition"]

    # Verify content does not expose internal MinIO hostnames
    data = resp.json()
    assert data["graph_type"] == "AST"
    assert "minio" not in resp.text.lower()


@pytest.mark.asyncio
async def test_artifact_download_cannot_cross_organizations(
    client: AsyncClient, db_session: AsyncSession
):
    """User in Org A cannot download artifact from Org B."""
    tenant_a = await create_tenant_environment(db_session, "OrgA")
    tenant_b = await create_tenant_environment(db_session, "OrgB")

    scan_b_id = str(tenant_b["scan"].id)
    art_b_id = str(tenant_b["artifacts"]["AST"].id)

    resp = await client.get(
        f"/api/v1/scans/{scan_b_id}/artifacts/{art_b_id}/download",
        headers=tenant_a["headers"]["owner"],
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_artifact_download_cannot_download_wrong_scan_artifact(
    client: AsyncClient, db_session: AsyncSession
):
    """Passing an artifact ID that does not belong to the scan returns 404."""
    tenant = await create_tenant_environment(db_session, "ScanMismatch")
    scan_id = str(tenant["scan"].id)
    random_art_id = str(uuid.uuid4())

    resp = await client.get(
        f"/api/v1/scans/{scan_id}/artifacts/{random_art_id}/download",
        headers=tenant["headers"]["developer"],
    )
    assert resp.status_code == 404


# ── 5. PDG Truthfulness & Separation ──────────────────────────


@pytest.mark.asyncio
async def test_pdg_truthful_state_and_canonical_graph_separation(
    client: AsyncClient, db_session: AsyncSession
):
    """Listing artifacts returns exactly 6 items (5 canonical graphs + 1 TAINT), with PDG marked unsupported."""
    tenant = await create_tenant_environment(db_session, "ArtifactCheck")
    scan_id = str(tenant["scan"].id)

    resp = await client.get(
        f"/api/v1/scans/{scan_id}/artifacts",
        headers=tenant["headers"]["viewer"],
    )
    assert resp.status_code == 200
    artifacts = resp.json()["data"]

    # Exactly 6 artifacts
    assert len(artifacts) == 6

    # 5 Canonical program representations
    canonical_types = {"AST", "CFG", "PDG", "CPG", "CALL_GRAPH"}
    found_types = {a["artifact_type"] for a in artifacts}
    assert canonical_types.issubset(found_types)
    assert "TAINT" in found_types

    # PDG status is truthfully 'unsupported' under native_ast_analyzer fallback
    pdg_art = next(a for a in artifacts if a["artifact_type"] == "PDG")
    assert pdg_art["status"] == "unsupported"
    assert pdg_art["metadata"].get("engine_fallback") is True
