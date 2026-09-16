# ============================================================
# Phase 2 RBAC & API Key Isolation Tests
# ============================================================

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.organization import OrganizationMember
from backend.app.models.rbac import Role
from backend.app.repositories.phase2_repositories import RbacRepository
from sqlalchemy import select


@pytest.mark.asyncio
async def test_viewer_role_has_read_only_access(client: AsyncClient, db_session: AsyncSession):
    """A Viewer can list/read projects, but is strictly blocked from mutations (e.g. project.create)."""
    # 1. Register Owner
    reg = await client.post(
        "/api/v1/auth/register",
        json={"name": "Org Lead", "email": "lead@org-viewer-test.com", "password": "LeadPassword123!"},
    )
    assert reg.status_code == 200
    owner_token = reg.json()["data"]["tokens"]["access_token"]
    org_id = reg.json()["data"]["organization"]["id"]

    # 2. Invite a Viewer
    invite_resp = await client.post(
        f"/api/v1/organizations/{org_id}/team/invitations",
        json={"email": "viewer@example.com", "role_name": "viewer"},
        headers={"Authorization": f"Bearer {owner_token}", "X-Organization-ID": org_id},
    )
    assert invite_resp.status_code == 201
    invite_token = invite_resp.json()["data"]["invitation_token"]

    # 3. Register Viewer account and accept invitation
    reg_viewer = await client.post(
        "/api/v1/auth/register",
        json={"name": "Viewer User", "email": "viewer@example.com", "password": "ViewerPassword123!"},
    )
    viewer_token = reg_viewer.json()["data"]["tokens"]["access_token"]
    viewer_headers = {"Authorization": f"Bearer {viewer_token}", "X-Organization-ID": org_id}

    accept_resp = await client.post(
        "/api/v1/invitations/accept",
        json={"token": invite_token},
        headers=viewer_headers,
    )
    assert accept_resp.status_code == 200

    # 4. Viewer can read/list projects
    list_resp = await client.get("/api/v1/projects", headers=viewer_headers)
    assert list_resp.status_code == 200

    # 5. Viewer CANNOT create projects (fails with 403 Forbidden)
    create_resp = await client.post(
        "/api/v1/projects",
        json={"name": "Illegal Viewer Project"},
        headers=viewer_headers,
    )
    assert create_resp.status_code == 403
    assert "Permission denied" in create_resp.json()["message"]


@pytest.mark.asyncio
async def test_developer_role_cannot_manage_team(client: AsyncClient, db_session: AsyncSession):
    """A Developer can create projects, but cannot invite or manage team members."""
    # 1. Register Owner
    reg = await client.post(
        "/api/v1/auth/register",
        json={"name": "Dev Test Owner", "email": "owner@dev-rbac.com", "password": "OwnerPassword123!"},
    )
    owner_token = reg.json()["data"]["tokens"]["access_token"]
    org_id = reg.json()["data"]["organization"]["id"]

    # 2. Invite Developer
    invite_resp = await client.post(
        f"/api/v1/organizations/{org_id}/team/invitations",
        json={"email": "dev1@example.com", "role_name": "developer"},
        headers={"Authorization": f"Bearer {owner_token}", "X-Organization-ID": org_id},
    )
    invite_token = invite_resp.json()["data"]["invitation_token"]

    # 3. Register and accept
    reg_dev = await client.post(
        "/api/v1/auth/register",
        json={"name": "Dev User", "email": "dev1@example.com", "password": "DevPassword123!"},
    )
    dev_token = reg_dev.json()["data"]["tokens"]["access_token"]
    dev_headers = {"Authorization": f"Bearer {dev_token}", "X-Organization-ID": org_id}

    await client.post("/api/v1/invitations/accept", json={"token": invite_token}, headers=dev_headers)

    # 4. Developer CAN read projects in org
    list_proj = await client.get("/api/v1/projects", headers=dev_headers)
    assert list_proj.status_code == 200

    # 5. Developer CANNOT invite team members (fails 403)
    invite_fail = await client.post(
        f"/api/v1/organizations/{org_id}/team/invitations",
        json={"email": "intruder@example.com", "role_name": "developer"},
        headers=dev_headers,
    )
    assert invite_fail.status_code == 403


@pytest.mark.asyncio
async def test_api_key_lifecycle_and_secret_protection(client: AsyncClient, db_session: AsyncSession):
    """API key secret is returned only once at creation; metadata listing never leaks the secret."""
    # 1. Register Owner
    reg = await client.post(
        "/api/v1/auth/register",
        json={"name": "API Key Admin", "email": "apikey@test.com", "password": "ApiKeyPassword123!"},
    )
    token = reg.json()["data"]["tokens"]["access_token"]
    org_id = reg.json()["data"]["organization"]["id"]
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": org_id}

    # 2. Create API Key
    create_resp = await client.post(
        f"/api/v1/organizations/{org_id}/api-keys",
        json={"name": "CI Deployment Key", "expires_in_days": 30},
        headers=headers,
    )
    assert create_resp.status_code == 201
    created_data = create_resp.json()["data"]
    raw_key = created_data["api_key"]
    key_id = created_data["id"]
    prefix = created_data["key_prefix"]

    assert raw_key.startswith(f"{prefix}_")
    assert len(raw_key) > 30

    # 3. List API Keys -> verify secret is NOT returned in list metadata
    list_resp = await client.get(
        f"/api/v1/organizations/{org_id}/api-keys",
        headers=headers,
    )
    assert list_resp.status_code == 200
    keys = list_resp.json()["data"]
    assert len(keys) == 1
    assert keys[0]["id"] == key_id
    assert keys[0]["key_prefix"] == prefix
    assert "api_key" not in keys[0]
    assert "hashed_key" not in keys[0]

    # 4. Revoke API Key
    del_resp = await client.delete(
        f"/api/v1/organizations/{org_id}/api-keys/{key_id}",
        headers=headers,
    )
    assert del_resp.status_code == 200

    # 5. Verify status is revoked
    relist_resp = await client.get(
        f"/api/v1/organizations/{org_id}/api-keys",
        headers=headers,
    )
    assert relist_resp.json()["data"][0]["revoked_at"] is not None


@pytest.mark.asyncio
async def test_audit_logs_record_security_events(client: AsyncClient, db_session: AsyncSession):
    """Sensitive security operations generate durable audit events without logging raw secrets."""
    # 1. Register Owner
    reg = await client.post(
        "/api/v1/auth/register",
        json={"name": "Audit Tester", "email": "audit@test.com", "password": "AuditPassword123!"},
    )
    token = reg.json()["data"]["tokens"]["access_token"]
    org_id = reg.json()["data"]["organization"]["id"]
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": org_id}

    # 2. Create project
    await client.post(
        "/api/v1/projects",
        json={"name": "Audited Project Alpha"},
        headers=headers,
    )

    # 3. Fetch audit logs
    audit_resp = await client.get(
        f"/api/v1/organizations/{org_id}/audit",
        headers=headers,
    )
    assert audit_resp.status_code == 200
    logs = audit_resp.json()["data"]
    assert len(logs) >= 2  # user.registered and project.created

    actions = [entry["action"] for entry in logs]
    assert "project.created" in actions

    # Ensure no secrets leak in audit metadata
    for entry in logs:
        metadata_str = str(entry.get("metadata", {}))
        assert "password" not in metadata_str
        assert "token" not in metadata_str
        assert "secret" not in metadata_str
