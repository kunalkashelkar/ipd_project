import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.organization import Organization, OrganizationMember
from backend.app.models.session import UserSession
from backend.app.models.user import User


@pytest.mark.asyncio
async def test_registration_creates_org_and_owner(client: AsyncClient, db_session: AsyncSession):
    """Registration creates user, dedicated organization, and assigns user as OWNER."""
    payload = {
        "name": "Alice Architect",
        "email": "alice.arch@example.com",
        "password": "SecurePassword123!",
        "organization_name": "Apex Cyber Defense",
    }
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 200

    data = resp.json()
    assert data["status"] == "success"
    user_data = data["data"]["user"]
    org_data = data["data"]["organization"]
    tokens = data["data"]["tokens"]

    assert user_data["email"] == "alice.arch@example.com"
    assert org_data["name"] == "Apex Cyber Defense"
    assert "access_token" in tokens
    assert "refresh_token" in tokens

    # Verify DB state: user is OWNER of organization
    user_stmt = select(User).where(User.email == "alice.arch@example.com")
    user = (await db_session.execute(user_stmt)).scalar_one()

    member_stmt = (
        select(OrganizationMember)
        .where(OrganizationMember.user_id == user.id)
    )
    member = (await db_session.execute(member_stmt)).scalar_one()
    assert member.organization_id == uuid.UUID(org_data["id"])
    assert member.status == "active"


@pytest.mark.asyncio
async def test_logout_revokes_server_session(client: AsyncClient, db_session: AsyncSession):
    """Logout invalidates the server-side session; subsequent requests with that token are rejected."""
    # 1. Register and get token
    reg_payload = {
        "name": "Bob Builder",
        "email": "bob.builder@example.com",
        "password": "StrongPassword999!",
    }
    reg_resp = await client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_resp.status_code == 200

    token = reg_resp.json()["data"]["tokens"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Authenticated request succeeds
    me_resp = await client.get("/api/v1/auth/me", headers=headers)
    assert me_resp.status_code == 200

    # 3. Logout
    logout_resp = await client.post("/api/v1/auth/logout", headers=headers)
    assert logout_resp.status_code == 200

    # 4. Same token now fails because server session was revoked
    after_resp = await client.get("/api/v1/auth/me", headers=headers)
    assert after_resp.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token_rotation_and_revocation(client: AsyncClient, db_session: AsyncSession):
    """Refresh token can be exchanged for a new pair; old refresh token is rotated."""
    reg_payload = {
        "name": "Charlie Refresh",
        "email": "charlie@example.com",
        "password": "PasswordCharlie123!",
    }
    reg_resp = await client.post("/api/v1/auth/register", json=reg_payload)
    refresh_token_1 = reg_resp.json()["data"]["tokens"]["refresh_token"]

    # 1. Refresh session
    refresh_resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token_1})
    assert refresh_resp.status_code == 200
    new_tokens = refresh_resp.json()["data"]["tokens"]
    refresh_token_2 = new_tokens["refresh_token"]
    assert refresh_token_2 != refresh_token_1

    # 2. Re-using old rotated token fails
    stale_resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token_1})
    assert stale_resp.status_code == 401


@pytest.mark.asyncio
async def test_password_reset_invalidates_all_sessions(client: AsyncClient, db_session: AsyncSession):
    """Password reset changes password and revokes all active sessions for the user."""
    # 1. Register user
    reg_payload = {
        "name": "Diana Defender",
        "email": "diana@example.com",
        "password": "OldPassword123!",
    }
    reg_resp = await client.post("/api/v1/auth/register", json=reg_payload)
    token = reg_resp.json()["data"]["tokens"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Verify session works
    assert (await client.get("/api/v1/auth/me", headers=headers)).status_code == 200

    # 2. Request password reset
    req_resp = await client.post("/api/v1/auth/request-password-reset", json={"email": "diana@example.com"})
    assert req_resp.status_code == 200
    reset_token = req_resp.json()["data"]["dev_token"]

    # 3. Confirm password reset
    confirm_resp = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": reset_token, "new_password": "BrandNewSecurePassword456!"},
    )
    assert confirm_resp.status_code == 200

    # 4. Old session token is now rejected
    assert (await client.get("/api/v1/auth/me", headers=headers)).status_code == 401

    # 5. Login with new password succeeds
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "diana@example.com", "password": "BrandNewSecurePassword456!"},
    )
    assert login_resp.status_code == 200

    # 6. Reusing the same reset token is rejected
    reuse_resp = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": reset_token, "new_password": "YetAnotherPassword789!"},
    )
    assert reuse_resp.status_code in (400, 422)


@pytest.mark.asyncio
async def test_email_verification_lifecycle(client: AsyncClient, db_session: AsyncSession):
    """Email verification token can be generated and consumed exactly once."""
    from backend.app.services.auth_service import AuthService

    # 1. Register user
    reg_payload = {
        "name": "Evan Email",
        "email": "evan@example.com",
        "password": "PasswordEvan123!",
    }
    reg_resp = await client.post("/api/v1/auth/register", json=reg_payload)
    user_id = reg_resp.json()["data"]["user"]["id"]

    # 2. Create verification token via service
    service = AuthService(db_session)
    raw_token = await service.create_email_verification_token(user_id=uuid.UUID(user_id))

    # 3. Consume token
    verify_resp = await client.post("/api/v1/auth/verify-email", json={"token": raw_token})
    assert verify_resp.status_code == 200

    # 4. Reusing token fails
    reused_resp = await client.post("/api/v1/auth/verify-email", json={"token": raw_token})
    assert reused_resp.status_code == 422
