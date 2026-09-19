# ============================================================
# Phase 1-7 Cross-Tenant Negative Security Matrix Tests
# ============================================================
# Exhaustively proves that User B (Organization B) cannot access
# any resource of Organization A, even when providing known internal
# UUIDs or public IDs.
# ============================================================

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.finding import Finding, FindingOccurrence, FindingComment, FindingAssignment
from backend.app.models.organization import Organization, OrganizationMember
from backend.app.models.project import Project
from backend.app.models.repository import Repository
from backend.app.models.scan import Scan
from backend.app.models.security_gate import PRSecurityResult, SecurityGatePolicy
from backend.app.models.source_snapshot import SourceSnapshot
from backend.app.models.notification import Notification
from backend.app.models.report import Report, ReportFile
from backend.app.models.remediation import Remediation, RemediationValidation
from backend.app.models.user import User


@pytest.mark.asyncio
async def test_cross_tenant_isolation_matrix_all_resources(client: AsyncClient, db_session: AsyncSession):
    """Deep negative test matrix verifying Tenant A data cannot be accessed by Tenant B."""

    # 1. Setup Tenant A
    reg_a = await client.post(
        "/api/v1/auth/register",
        json={"name": "Alice Corp", "email": "alice@corp-a.com", "password": "SecurePasswordA123!", "organization_name": "Corp A"},
    )
    assert reg_a.status_code == 200
    token_a = reg_a.json()["data"]["tokens"]["access_token"]
    org_a_id = uuid.UUID(reg_a.json()["data"]["organization"]["id"])
    headers_a = {"Authorization": f"Bearer {token_a}", "X-Organization-ID": str(org_a_id)}

    # 2. Setup Tenant B
    reg_b = await client.post(
        "/api/v1/auth/register",
        json={"name": "Bob Corp", "email": "bob@corp-b.com", "password": "SecurePasswordB123!", "organization_name": "Corp B"},
    )
    assert reg_b.status_code == 200
    token_b = reg_b.json()["data"]["tokens"]["access_token"]
    org_b_id = uuid.UUID(reg_b.json()["data"]["organization"]["id"])
    headers_b = {"Authorization": f"Bearer {token_b}", "X-Organization-ID": str(org_b_id)}

    # 3. Create Tenant A Resources in DB
    user_a_stmt = await db_session.execute(
        OrganizationMember.__table__.select().where(OrganizationMember.organization_id == org_a_id)
    )
    user_a_row = user_a_stmt.first()
    user_a_id = user_a_row.user_id

    # Project A
    proj_a = Project(
        id=uuid.uuid4(),
        organization_id=org_a_id,
        name="Corp A Proprietary Software",
        owner_id=user_a_id,
        language="python",
        is_archived=False,
    )
    db_session.add(proj_a)
    await db_session.commit()
    await db_session.refresh(proj_a)

    # Repository A
    repo_a = Repository(
        id=uuid.uuid4(),
        project_id=proj_a.id,
        provider="github",
        repository_url="https://github.com/corp-a/proprietary.git",
        branch="main",
        status="connected",
    )
    db_session.add(repo_a)
    await db_session.commit()
    await db_session.refresh(repo_a)

    # Snapshot A
    snap_a = SourceSnapshot(
        id=uuid.uuid4(),
        project_id=proj_a.id,
        source_type="git",
        source_version="commit_sha_corp_a",
        content_hash="a" * 64,
        artifact_uri="snapshots/corp_a/snap.zip",
        status="ready",
    )
    db_session.add(snap_a)
    await db_session.commit()
    await db_session.refresh(snap_a)

    # Scan A
    scan_a = Scan(
        id=uuid.uuid4(),
        project_id=proj_a.id,
        organization_id=org_a_id,
        source_snapshot_id=snap_a.id,
        status="completed",
    )
    db_session.add(scan_a)
    await db_session.commit()
    await db_session.refresh(scan_a)

    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)

    # Finding A
    find_a = Finding(
        id=uuid.uuid4(),
        project_id=proj_a.id,
        organization_id=org_a_id,
        title="Corp A Internal Secret Exposure",
        vulnerability_type="HARDCODED_KEY",
        severity="critical",
        status="OPEN",
        fingerprint="fp_corp_a_secret",
        first_seen_at=now,
        last_seen_at=now,
    )
    db_session.add(find_a)
    await db_session.commit()
    await db_session.refresh(find_a)

    # Report A
    rpt_a = Report(
        id=uuid.uuid4(),
        project_id=proj_a.id,
        organization_id=org_a_id,
        scan_id=scan_a.id,
        report_type="security",
        status="completed",
    )
    db_session.add(rpt_a)
    await db_session.commit()
    await db_session.refresh(rpt_a)

    # Notification A
    notif_a = Notification(
        id=uuid.uuid4(),
        user_id=user_a_id,
        organization_id=org_a_id,
        type="critical_finding",
        title="Corp A Critical Secret",
        severity="critical",
    )
    db_session.add(notif_a)
    await db_session.commit()
    await db_session.refresh(notif_a)

    # 4. EXHAUSTIVE TENANT B NEGATIVE ACCESS CHECKS

    # A. Project isolation
    r_proj = await client.get(f"/api/v1/projects/{proj_a.id}", headers=headers_b)
    assert r_proj.status_code in (403, 404)
    r_proj_pub = await client.get(f"/api/v1/projects/{proj_a.public_id}", headers=headers_b)
    assert r_proj_pub.status_code in (403, 404)

    # B. Repository isolation
    r_repo = await client.get(f"/api/v1/repositories/{repo_a.id}", headers=headers_b)
    assert r_repo.status_code in (403, 404)

    # C. Snapshot isolation
    r_snap = await client.get(f"/api/v1/snapshots/{snap_a.id}", headers=headers_b)
    assert r_snap.status_code in (403, 404)

    # D. Scan isolation
    r_scan = await client.get(f"/api/v1/scans/{scan_a.id}", headers=headers_b)
    assert r_scan.status_code in (403, 404)
    r_scan_pub = await client.get(f"/api/v1/scans/{scan_a.public_id}", headers=headers_b)
    assert r_scan_pub.status_code in (403, 404)

    # E. Finding isolation
    r_find = await client.get(f"/api/v1/findings/{find_a.id}", headers=headers_b)
    assert r_find.status_code in (403, 404)
    r_find_pub = await client.get(f"/api/v1/findings/{find_a.public_id}", headers=headers_b)
    assert r_find_pub.status_code in (403, 404)

    # F. Report isolation
    r_rpt = await client.get(f"/api/v1/reports/{rpt_a.id}", headers=headers_b)
    assert r_rpt.status_code in (403, 404)
    r_rpt_pub = await client.get(f"/api/v1/reports/{rpt_a.public_id}", headers=headers_b)
    assert r_rpt_pub.status_code in (403, 404)

    # G. Report download isolation
    r_dl = await client.get(f"/api/v1/reports/{rpt_a.public_id}/download", headers=headers_b)
    assert r_dl.status_code in (403, 404)

    # H. Project Analytics isolation
    r_ana = await client.get(f"/api/v1/projects/{proj_a.id}/analytics", headers=headers_b)
    assert r_ana.status_code in (403, 404)

    # I. Gate policy isolation
    r_gate = await client.get(f"/api/v1/projects/{proj_a.id}/gate-policy", headers=headers_b)
    assert r_gate.status_code in (403, 404)

    # J. PR results isolation
    r_pr = await client.get(f"/api/v1/projects/{proj_a.id}/pr-results", headers=headers_b)
    assert r_pr.status_code in (403, 404)
