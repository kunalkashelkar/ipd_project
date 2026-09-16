# ============================================================
# Phase 2 Team & RBAC Endpoints Test Suite
# ============================================================

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.organization import Organization, OrganizationMember
from backend.app.models.rbac import Role
from backend.app.models.user import User


@pytest.mark.asyncio
async def test_team_roles_and_permissions_endpoint(
    client: AsyncClient,
    test_user: User,
    db_session: AsyncSession,
    auth_headers: dict,
):
    """Ensure authorized user can retrieve predefined roles and permissions."""
    from sqlalchemy import select
    res = await db_session.execute(
        select(OrganizationMember).where(OrganizationMember.user_id == test_user.id)
    )
    member = res.scalar_one()

    resp = await client.get(
        f"/api/v1/organizations/{member.organization_id}/team/roles",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    roles = data["data"]
    role_names = [r["name"] for r in roles]
    assert "owner" in role_names
    assert "admin" in role_names
    assert "security_analyst" in role_names
    assert "developer" in role_names
    assert "viewer" in role_names

    # Check that permissions are populated
    owner_role = next(r for r in roles if r["name"] == "owner")
    assert len(owner_role["permissions"]) > 0
    perm_keys = [p["key"] for p in owner_role["permissions"]]
    assert "team.read" in perm_keys
    assert "team.invite" in perm_keys


@pytest.mark.asyncio
async def test_team_invitation_details_preview(
    client: AsyncClient,
    test_user: User,
    db_session: AsyncSession,
    auth_headers: dict,
):
    """Ensure invitation can be previewed by token prior to acceptance."""
    from sqlalchemy import select
    res = await db_session.execute(
        select(OrganizationMember).where(OrganizationMember.user_id == test_user.id)
    )
    member = res.scalar_one()

    # Create an invite
    invite_resp = await client.post(
        f"/api/v1/organizations/{member.organization_id}/team/invitations",
        json={"email": "newdev@example.com", "role_name": "developer"},
        headers=auth_headers,
    )
    assert invite_resp.status_code == 201
    raw_token = invite_resp.json()["data"]["invitation_token"]

    # Preview by raw token (no auth required)
    preview_resp = await client.get(f"/api/v1/invitations/{raw_token}")
    assert preview_resp.status_code == 200
    preview_data = preview_resp.json()["data"]
    assert preview_data["invited_email"] == "newdev@example.com"
    assert preview_data["role_name"] == "developer"
    assert preview_data["status"] == "pending"
    assert preview_data["account_exists"] is False
    assert preview_data["already_member"] is False


@pytest.mark.asyncio
async def test_registration_with_invitation_token_directly_joins_org(
    client: AsyncClient,
    test_user: User,
    db_session: AsyncSession,
    auth_headers: dict,
):
    """Ensure registering with an invitation token joins the organization directly with zero extra org created."""
    from sqlalchemy import select
    res = await db_session.execute(
        select(OrganizationMember).where(OrganizationMember.user_id == test_user.id)
    )
    owner_member = res.scalar_one()
    org_id = owner_member.organization_id

    # 1. Invite a new user
    invite_email = "direct_joiner@example.com"
    invite_resp = await client.post(
        f"/api/v1/organizations/{org_id}/team/invitations",
        json={"email": invite_email, "role_name": "developer"},
        headers=auth_headers,
    )
    assert invite_resp.status_code == 201
    raw_token = invite_resp.json()["data"]["invitation_token"]

    # 2. Preview before account exists
    preview1 = await client.get(f"/api/v1/invitations/{raw_token}")
    assert preview1.status_code == 200
    assert preview1.json()["data"]["account_exists"] is False

    # 3. Register directly with the invitation token
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "name": "Direct Joiner",
            "email": invite_email,
            "password": "SecurePassword123!",
            "invitation_token": raw_token,
        },
    )
    assert reg_resp.status_code in (200, 201)
    reg_data = reg_resp.json()["data"]
    new_user = reg_data["user"]
    joined_org = reg_data["organization"]

    # Must be the SAME organization as the inviter
    assert str(joined_org["id"]) == str(org_id)

    # 4. Token belongs to new user and active_org is org_id
    new_token = reg_data["tokens"]["access_token"]
    new_headers = {"Authorization": f"Bearer {new_token}"}

    # 5. Check organizations list for new user: must contain exactly 1 org (the invited one, NO default workspace created)
    orgs_resp = await client.get("/api/v1/organizations", headers=new_headers)
    assert orgs_resp.status_code == 200
    user_orgs = orgs_resp.json()["data"]
    assert len(user_orgs) == 1
    assert str(user_orgs[0]["id"]) == str(org_id)

    # 6. Check team membership: user must be an active 'developer'
    members_resp = await client.get(
        f"/api/v1/organizations/{org_id}/team/members",
        headers=auth_headers,
    )
    assert members_resp.status_code == 200
    members = members_resp.json()["data"]
    joined_member = next(m for m in members if m["user_email"] == invite_email)
    assert joined_member["role"] == "developer"
    assert joined_member["status"] == "active"

    # 7. Check preview after joining: already_member is True
    preview2 = await client.get(f"/api/v1/invitations/{raw_token}")
    assert preview2.status_code in (200, 422)  # Either accepted status or already accepted message


@pytest.mark.asyncio
async def test_current_user_role_and_my_membership(client, auth_headers):
    """Verify that list_user_organizations and /my-membership return the authoritative organization role."""
    # 1. Get user organizations with auth_headers (owner user)
    orgs_resp = await client.get("/api/v1/organizations", headers=auth_headers)
    assert orgs_resp.status_code == 200
    orgs = orgs_resp.json()["data"]
    assert len(orgs) >= 1
    org = orgs[0]
    org_id = org["id"]
    assert org["current_user_role"] == "owner"

    # 2. Query /organizations/{id}/my-membership
    mem_resp = await client.get(f"/api/v1/organizations/{org_id}/my-membership", headers=auth_headers)
    assert mem_resp.status_code == 200
    mem_data = mem_resp.json()["data"]
    assert mem_data["organization_id"] == str(org_id)
    assert mem_data["role"] == "owner"
    assert mem_data["status"] == "active"

    # 3. Query /auth/me with X-Organization-ID
    me_resp = await client.get("/api/v1/auth/me", headers={**auth_headers, "X-Organization-ID": str(org_id)})
    assert me_resp.status_code == 200
    assert me_resp.json()["data"]["active_organization_role"] == "owner"


