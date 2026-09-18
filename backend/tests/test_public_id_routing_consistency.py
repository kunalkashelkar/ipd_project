# ============================================================
# test_public_id_routing_consistency.py
# Validates public ID generation, dual UUID/public-ID lookup,
# cross-tenant security, and response field population.
# ============================================================

from __future__ import annotations

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.identifiers import (
    generate_public_id,
    PREFIX_PROJECT,
    PREFIX_SCAN,
    PREFIX_SNAPSHOT,
    PREFIX_FINDING,
    parse_public_id,
)
from backend.app.models.organization import Organization, OrganizationMember
from backend.app.models.project import Project
from backend.app.models.source_snapshot import SourceSnapshot
from backend.app.models.scan import Scan
from backend.app.models.finding import Finding
from backend.app.models.user import User
from backend.app.models.rbac import Role
from backend.app.core.security import create_token_pair


@pytest.mark.asyncio
async def test_public_id_format_consistency():
    """Verify all public ID prefixes match the canonical format."""
    prj_id = generate_public_id(PREFIX_PROJECT)
    scn_id = generate_public_id(PREFIX_SCAN)
    snp_id = generate_public_id(PREFIX_SNAPSHOT)
    fnd_id = generate_public_id(PREFIX_FINDING)

    assert prj_id.startswith("prj_")
    assert scn_id.startswith("scn_")
    assert snp_id.startswith("snp_")
    assert fnd_id.startswith("fnd_")

    prefix, raw = parse_public_id(fnd_id)
    assert prefix == "fnd"
    assert len(raw) == 12


@pytest.mark.asyncio
async def test_finding_dual_resolution_and_tenant_safety(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """Verify finding endpoint resolves by public_id and rejects cross-tenant access."""
    # Org A & User A
    org_a = Organization(id=uuid.uuid4(), name="Org A", slug=f"org-a-{uuid.uuid4().hex[:6]}")
    user_a = User(
        id=uuid.uuid4(),
        name="User A",
        email=f"usera-{uuid.uuid4().hex[:6]}@example.com",
        password_hash="hash",
        status="active",
    )
    db_session.add_all([org_a, user_a])
    await db_session.flush()

    stmt = select(Role).where(Role.name == "owner")
    res = await db_session.execute(stmt)
    role_owner = res.scalar_one()

    member_a = OrganizationMember(
        id=uuid.uuid4(),
        organization_id=org_a.id,
        user_id=user_a.id,
        role_id=role_owner.id,
        status="active",
    )
    db_session.add(member_a)

    proj_a = Project(
        id=uuid.uuid4(),
        name="Project A",
        public_id=generate_public_id(PREFIX_PROJECT),
        organization_id=org_a.id,
        owner_id=user_a.id,
    )
    db_session.add(proj_a)
    await db_session.flush()

    snap_a = SourceSnapshot(
        id=uuid.uuid4(),
        public_id=generate_public_id(PREFIX_SNAPSHOT),
        project_id=proj_a.id,
        source_type="upload_zip",
        artifact_uri="snapshots/dummy.zip",
        content_hash="dummy-hash-1234567890abcdef",
        status="ready",
    )
    db_session.add(snap_a)
    await db_session.flush()

    scan_a = Scan(
        id=uuid.uuid4(),
        public_id=generate_public_id(PREFIX_SCAN),
        project_id=proj_a.id,
        organization_id=org_a.id,
        source_snapshot_id=snap_a.id,
        created_by=user_a.id,
        status="completed",
    )
    db_session.add(scan_a)
    await db_session.flush()

    finding_a = Finding(
        id=uuid.uuid4(),
        public_id=generate_public_id(PREFIX_FINDING),
        project_id=proj_a.id,
        organization_id=org_a.id,
        title="Command Injection",
        vulnerability_type="CWE-78",
        cwe_id="CWE-78",
        severity="critical",
        confidence=0.95,
        risk_score=9.0,
        risk_version="v1",
        status="OPEN",
        fingerprint="fp123456",
        fingerprint_version="v1",
        first_seen_at=scan_a.created_at,
        last_seen_at=scan_a.created_at,
    )
    db_session.add(finding_a)
    await db_session.commit()

    tokens_a = create_token_pair(str(user_a.id), str(org_a.id))
    headers_a = {"Authorization": f"Bearer {tokens_a['access_token']}"}

    # 1. Access finding via its public_id
    resp_pub = await client.get(f"/api/v1/findings/{finding_a.public_id}", headers=headers_a)
    assert resp_pub.status_code == 200, resp_pub.text
    data = resp_pub.json()["data"]
    assert data["public_id"] == finding_a.public_id
    assert data["id"] == str(finding_a.id)
    assert data["project_public_id"] == proj_a.public_id

    # 2. Access finding via its internal UUID (backward compatibility)
    resp_uuid = await client.get(f"/api/v1/findings/{finding_a.id}", headers=headers_a)
    assert resp_uuid.status_code == 200
    assert resp_uuid.json()["data"]["public_id"] == finding_a.public_id

    # 3. Org B & User B should NOT be able to access Org A's finding via public_id
    org_b = Organization(id=uuid.uuid4(), name="Org B", slug=f"org-b-{uuid.uuid4().hex[:6]}")
    user_b = User(
        id=uuid.uuid4(),
        name="User B",
        email=f"userb-{uuid.uuid4().hex[:6]}@example.com",
        password_hash="hash",
        status="active",
    )
    db_session.add_all([org_b, user_b])
    await db_session.flush()

    member_b = OrganizationMember(
        id=uuid.uuid4(),
        organization_id=org_b.id,
        user_id=user_b.id,
        role_id=role_owner.id,
        status="active",
    )
    db_session.add(member_b)
    await db_session.commit()

    tokens_b = create_token_pair(str(user_b.id), str(org_b.id))
    headers_b = {"Authorization": f"Bearer {tokens_b['access_token']}"}

    resp_cross = await client.get(f"/api/v1/findings/{finding_a.public_id}", headers=headers_b)
    assert resp_cross.status_code == 404


@pytest.mark.asyncio
async def test_project_and_scan_public_id_lookups(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """Verify projects and scans resolve by public_id and serialize canonical public IDs."""
    org = Organization(id=uuid.uuid4(), name="Lookup Org", slug=f"lookup-org-{uuid.uuid4().hex[:6]}")
    user = User(
        id=uuid.uuid4(),
        name="Lookup User",
        email=f"lookup-{uuid.uuid4().hex[:6]}@example.com",
        password_hash="hash",
        status="active",
    )
    db_session.add_all([org, user])
    await db_session.flush()

    stmt = select(Role).where(Role.name == "owner")
    res = await db_session.execute(stmt)
    role_owner = res.scalar_one()

    member = OrganizationMember(
        id=uuid.uuid4(),
        organization_id=org.id,
        user_id=user.id,
        role_id=role_owner.id,
        status="active",
    )
    db_session.add(member)

    proj = Project(
        id=uuid.uuid4(),
        name="Public Lookup Project",
        public_id=generate_public_id(PREFIX_PROJECT),
        organization_id=org.id,
        owner_id=user.id,
    )
    db_session.add(proj)
    await db_session.flush()

    snap = SourceSnapshot(
        id=uuid.uuid4(),
        public_id=generate_public_id(PREFIX_SNAPSHOT),
        project_id=proj.id,
        source_type="upload_zip",
        artifact_uri="snapshots/lookup.zip",
        content_hash="hash-lookup-123456",
        status="ready",
    )
    db_session.add(snap)
    await db_session.flush()

    scan = Scan(
        id=uuid.uuid4(),
        public_id=generate_public_id(PREFIX_SCAN),
        project_id=proj.id,
        organization_id=org.id,
        source_snapshot_id=snap.id,
        created_by=user.id,
        status="completed",
    )
    db_session.add(scan)
    await db_session.commit()

    tokens = create_token_pair(str(user.id), str(org.id))
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    # Access project via public_id
    p_resp = await client.get(f"/api/v1/projects/{proj.public_id}", headers=headers)
    assert p_resp.status_code == 200
    assert p_resp.json()["data"]["public_id"] == proj.public_id

    # Access project via UUID
    p_uuid_resp = await client.get(f"/api/v1/projects/{proj.id}", headers=headers)
    assert p_uuid_resp.status_code == 200
    assert p_uuid_resp.json()["data"]["public_id"] == proj.public_id

    # Access scan via public_id
    s_resp = await client.get(f"/api/v1/scans/{scan.public_id}", headers=headers)
    assert s_resp.status_code == 200
    scan_data = s_resp.json()["data"]
    assert scan_data["public_id"] == scan.public_id
    assert scan_data["project_public_id"] == proj.public_id
    assert scan_data["project_name"] == proj.name
    assert scan_data["source_snapshot_public_id"] == snap.public_id

    # Access scan via UUID
    s_uuid_resp = await client.get(f"/api/v1/scans/{scan.id}", headers=headers)
    assert s_uuid_resp.status_code == 200
    assert s_uuid_resp.json()["data"]["public_id"] == scan.public_id

    # Access snapshots endpoint using project.public_id
    snaps_resp = await client.get(f"/api/v1/projects/{proj.public_id}/snapshots", headers=headers)
    assert snaps_resp.status_code == 200
    snap_items = snaps_resp.json()["data"]["items"]
    assert len(snap_items) >= 1
    assert any(s["public_id"] == snap.public_id for s in snap_items)

    # Access repositories endpoint using project.public_id
    repos_resp = await client.get(f"/api/v1/projects/{proj.public_id}/repositories", headers=headers)
    assert repos_resp.status_code == 200

