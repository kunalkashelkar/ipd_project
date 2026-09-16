# ============================================================
# Authentication & RBAC Security Tests
# ============================================================

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_standard_user(client: AsyncClient):
    """Test standard public registration succeeds with non-privileged role."""
    payload = {
        "name": "Jane Developer",
        "email": "jane.dev@example.com",
        "password": "SecurePassword123!",
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["data"]["user"]["email"] == "jane.dev@example.com"
    assert data["data"]["user"]["role"] in ("researcher", "developer")
    assert "tokens" in data["data"]
    assert "access_token" in data["data"]["tokens"]


@pytest.mark.asyncio
async def test_admin_self_registration_is_blocked(client: AsyncClient):
    """CRITICAL SECURITY TEST: Ensure public registration cannot claim 'admin' role."""
    payload = {
        "name": "Attacker Trying Admin",
        "email": "attacker@example.com",
        "password": "Password123456!",
        "role": "admin",
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    # The registration request schema must reject the privileged role (422 Unprocessable Entity)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_success_and_failure(client: AsyncClient, test_user):
    """Test login authentication flow with valid and invalid passwords."""
    # 1. Successful login
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": test_user.email, "password": "password123"},
    )
    assert login_resp.status_code == 200
    assert "access_token" in login_resp.json()["data"]["tokens"]

    # 2. Failed login (bad password)
    fail_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": test_user.email, "password": "WrongPassword999!"},
    )
    assert fail_resp.status_code == 401


@pytest.mark.asyncio
async def test_unauthorized_access_blocked(client: AsyncClient):
    """Test protected endpoints reject unauthenticated requests with 401."""
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_authenticated_profile_access(client: AsyncClient, auth_headers: dict):
    """Test accessing protected /auth/me with valid Bearer token."""
    response = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["data"]["email"] == "researcher@example.com"
