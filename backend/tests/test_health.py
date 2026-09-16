# ============================================================
# Health & Readiness Endpoint Tests
# ============================================================

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_liveness(client: AsyncClient):
    """Test /health endpoint returns service metadata and 200 OK."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["data"]["app"] == "VulnScanBackend"
    assert data["data"]["status"] == "healthy"


@pytest.mark.asyncio
async def test_health_live_probe(client: AsyncClient):
    """Test /health/live probe returns alive status."""
    response = await client.get("/health/live")
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["alive"] is True


@pytest.mark.asyncio
async def test_health_readiness_response_structure(client: AsyncClient):
    """Test /health/ready checks dependencies and returns structured status."""
    response = await client.get("/health/ready")
    # Response code is either 200 (if dependencies connected) or 503 (if dependencies unavailable)
    assert response.status_code in (200, 503)
    data = response.json()
    assert "database" in data["data"]
    assert "redis" in data["data"]
    assert "ready" in data["data"]
