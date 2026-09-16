# ============================================================
# Phase 2 Tenant Isolation Security Tests (MANDATORY SUITE)
# ============================================================
# Proves that:
# 1. Organization A cannot access Organization B resources
# 2. Knowledge of UUIDs never bypasses membership and permission checks
# 3. Suspended or removed members immediately lose access
# 4. Sole Owner invariants are strictly protected against demotion/removal
# ============================================================

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_cross_tenant_isolation_attack_is_blocked(client: AsyncClient, db_session: AsyncSession):
    """MANDATORY ACCEPTANCE TEST:

    User A (Org A) vs User B (Org B).
    User B attempts to access Org A's organization details, projects, members, audit logs, and API keys
    using Org A's direct UUIDs. Every attempt MUST be blocked.
    """
    # ── 1. Create Tenant A (User A + Org A) ───────────────────
    reg_a = await client.post(
        "/api/v1/auth/register",
        json={"name": "Alice Tenant A", "email": "alice@tenant-a.com", "password": "PasswordA123!", "organization_name": "Org Alpha"},
    )
    assert reg_a.status_code == 200
    token_a = reg_a.json()["data"]["tokens"]["access_token"]
    org_a_id = reg_a.json()["data"]["organization"]["id"]
    headers_a = {"Authorization": f"Bearer {token_a}", "X-Organization-ID": org_a_id}

    # Create Project in Org A
    proj_a_resp = await client.post(
        "/api/v1/projects",
        json={"name": "Secret Core A", "description": "Top secret project in Org A"},
        headers=headers_a,
    )
    assert proj_a_resp.status_code == 201
    project_a_id = proj_a_resp.json()["data"]["id"]

    # Create API Key in Org A
    api_key_a_resp = await client.post(
        f"/api/v1/organizations/{org_a_id}/api-keys",
        json={"name": "Prod Key A"},
        headers=headers_a,
    )
    assert api_key_a_resp.status_code == 201
    key_a_id = api_key_a_resp.json()["data"]["id"]

    # ── 2. Create Tenant B (User B + Org B) ───────────────────
    reg_b = await client.post(
        "/api/v1/auth/register",
        json={"name": "Bob Tenant B", "email": "bob@tenant-b.com", "password": "PasswordB123!", "organization_name": "Org Beta"},
    )
    assert reg_b.status_code == 200

    token_b = reg_b.json()["data"]["tokens"]["access_token"]
    org_b_id = reg_b.json()["data"]["organization"]["id"]
    headers_b = {"Authorization": f"Bearer {token_b}", "X-Organization-ID": org_b_id}

    # ── 3. User B attacks Org A resources directly with UUIDs ───

    # Attack 1: User B tries to view Org A details
    resp = await client.get(f"/api/v1/organizations/{org_a_id}", headers=headers_b)
    assert resp.status_code in (403, 404)

    # Attack 2: User B tries to update Org A settings
    resp = await client.patch(
        f"/api/v1/organizations/{org_a_id}",
        json={"name": "Defaced Org Name"},
        headers=headers_b,
    )
    assert resp.status_code in (403, 404)

    # Attack 3: User B tries to list Org A's team members
    resp = await client.get(f"/api/v1/organizations/{org_a_id}/team/members", headers=headers_b)
    assert resp.status_code in (403, 404)

    # Attack 4: User B tries to invite an attacker into Org A
    resp = await client.post(
        f"/api/v1/organizations/{org_a_id}/team/invitations",
        json={"email": "hacker@evil.com", "role_name": "admin"},
        headers=headers_b,
    )
    assert resp.status_code in (403, 404)

    # Attack 5: User B tries to access Org A's Project by UUID
    resp = await client.get(f"/api/v1/projects/{project_a_id}", headers=headers_b)
    assert resp.status_code == 404  # Must return 404 to avoid leaking existence

    # Attack 6: User B tries to modify Org A's Project
    resp = await client.patch(
        f"/api/v1/projects/{project_a_id}",
        json={"name": "Compromised Project"},
        headers=headers_b,
    )
    assert resp.status_code == 404

    # Attack 7: User B tries to inspect Org A's audit history
    resp = await client.get(f"/api/v1/organizations/{org_a_id}/audit", headers=headers_b)
    assert resp.status_code in (403, 404)

    # Attack 8: User B tries to list or revoke Org A's API keys
    resp = await client.get(f"/api/v1/organizations/{org_a_id}/api-keys", headers=headers_b)
    assert resp.status_code in (403, 404)

    resp = await client.delete(f"/api/v1/organizations/{org_a_id}/api-keys/{key_a_id}", headers=headers_b)
    assert resp.status_code in (403, 404)


@pytest.mark.asyncio
async def test_owner_invariants_protected(client: AsyncClient, db_session: AsyncSession):
    """Owner invariants: Cannot remove or demote the sole owner of an organization."""
    # 1. Register Org Owner
    reg = await client.post(
        "/api/v1/auth/register",
        json={"name": "Sole Owner", "email": "owner@solitary.com", "password": "OwnerPassword123!", "organization_name": "Single Owner Corp"},
    )
    assert reg.status_code == 200
    token = reg.json()["data"]["tokens"]["access_token"]
    org_id = reg.json()["data"]["organization"]["id"]
    user_id = reg.json()["data"]["user"]["id"]
    headers = {"Authorization": f"Bearer {token}", "X-Organization-ID": org_id}

    # 2. Attempt to demote sole owner to developer -> MUST FAIL
    demote_resp = await client.patch(
        f"/api/v1/organizations/{org_id}/team/members/{user_id}/role",
        json={"role_name": "developer"},
        headers=headers,
    )
    assert demote_resp.status_code == 422

    # 3. Attempt to remove sole owner -> MUST FAIL
    remove_resp = await client.delete(
        f"/api/v1/organizations/{org_id}/team/members/{user_id}",
        headers=headers,
    )
    assert remove_resp.status_code == 422


@pytest.mark.asyncio
async def test_invitation_and_membership_lifecycle(client: AsyncClient, db_session: AsyncSession):
    """Test inviting a user, accepting invitation, role change, and member removal."""
    # 1. Register Owner
    reg_owner = await client.post(
        "/api/v1/auth/register",
        json={"name": "Team Owner", "email": "team.owner@example.com", "password": "OwnerPassword123!"},
    )
    assert reg_owner.status_code == 200
    owner_token = reg_owner.json()["data"]["tokens"]["access_token"]
    org_id = reg_owner.json()["data"]["organization"]["id"]
    owner_headers = {"Authorization": f"Bearer {owner_token}", "X-Organization-ID": org_id}

    # 2. Invite Developer
    invite_resp = await client.post(
        f"/api/v1/organizations/{org_id}/team/invitations",
        json={"email": "new.dev@example.com", "role_name": "developer"},
        headers=owner_headers,
    )
    assert invite_resp.status_code == 201
    raw_invite_token = invite_resp.json()["data"]["invitation_token"]

    # 3. Register New Developer Account
    reg_dev = await client.post(
        "/api/v1/auth/register",
        json={"name": "New Developer", "email": "new.dev@example.com", "password": "DevPassword123!"},
    )
    assert reg_dev.status_code == 200

    dev_token = reg_dev.json()["data"]["tokens"]["access_token"]
    dev_headers = {"Authorization": f"Bearer {dev_token}"}

    # 4. Accept Invitation
    accept_resp = await client.post(
        "/api/v1/invitations/accept",
        json={"token": raw_invite_token},
        headers=dev_headers,
    )
    assert accept_resp.status_code == 200

    # 5. Developer can now list projects in Org
    dev_org_headers = {"Authorization": f"Bearer {dev_token}", "X-Organization-ID": org_id}
    proj_list_resp = await client.get("/api/v1/projects", headers=dev_org_headers)
    assert proj_list_resp.status_code == 200

    # 6. Developer cannot invite members (requires team.invite permission)
    unauthorized_invite = await client.post(
        f"/api/v1/organizations/{org_id}/team/invitations",
        json={"email": "third@example.com", "role_name": "viewer"},
        headers=dev_org_headers,
    )
    assert unauthorized_invite.status_code == 403

    # 7. Owner removes Developer
    dev_user_id = reg_dev.json()["data"]["user"]["id"]
    remove_resp = await client.delete(
        f"/api/v1/organizations/{org_id}/team/members/{dev_user_id}",
        headers=owner_headers,
    )
    assert remove_resp.status_code == 200

    # 8. Removed Developer immediately loses access
    after_remove_resp = await client.get("/api/v1/projects", headers=dev_org_headers)
    assert after_remove_resp.status_code == 403
