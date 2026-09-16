# ============================================================
# Scan API Foundation Tests — Input Validation & Honest State
# ============================================================

import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.project import Project


@pytest_asyncio.fixture
async def project_for_scan(db_session: AsyncSession, test_user) -> Project:
    """Create a project owned by the test user within their organization."""
    from backend.app.models.organization import OrganizationMember
    from sqlalchemy import select

    stmt = select(OrganizationMember).where(OrganizationMember.user_id == test_user.id)
    res = await db_session.execute(stmt)
    member = res.scalar_one()

    project = Project(
        organization_id=member.organization_id,
        name="Security Audit Target",
        owner_id=test_user.id,
        created_by=test_user.id,
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project



@pytest.mark.asyncio
async def test_scan_create_requires_target(
    client: AsyncClient, project_for_scan: Project, auth_headers: dict
):
    """Test scan creation fails when neither upload_id nor repository_id is provided."""
    payload = {
        "project_id": str(project_for_scan.id),
    }
    response = await client.post("/api/v1/scans", json=payload, headers=auth_headers)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_scan_list_unauthorized(client: AsyncClient):
    """Test unauthenticated scan listing is rejected."""
    response = await client.get("/api/v1/scans")
    assert response.status_code == 401
