# ============================================================
# Phase 2 Database Constraint & Relational Integrity Tests
# ============================================================

from __future__ import annotations

import uuid
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.organization import Organization, OrganizationMember
from backend.app.models.project import Project
from backend.app.models.rbac import Permission, Role, RolePermission
from backend.app.models.repository import Repository
from backend.app.models.git_meta import RepositoryBranch
from backend.app.models.user import User


@pytest.mark.asyncio
async def test_duplicate_user_email_rejected_at_db(db_session: AsyncSession):
    """Database unique constraint on user.email rejects duplicates."""
    user1 = User(
        email="test.dup@example.com",
        name="User One",
        password_hash="fakehash1",
        role="developer",
    )
    db_session.add(user1)
    await db_session.commit()

    user2 = User(
        email="test.dup@example.com",
        name="User Two",
        password_hash="fakehash2",
        role="developer",
    )
    db_session.add(user2)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_duplicate_organization_slug_rejected(db_session: AsyncSession):
    """Database unique constraint on organization.slug rejects duplicates."""
    org1 = Organization(name="Org One", slug="shared-slug")
    db_session.add(org1)
    await db_session.commit()

    org2 = Organization(name="Org Two", slug="shared-slug")
    db_session.add(org2)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_duplicate_organization_membership_rejected(db_session: AsyncSession):
    """Unique constraint uq_user_org_membership rejects duplicate active memberships."""
    # Create user and org
    user = User(email="member.dup@example.com", name="Member Dup", password_hash="h")
    org = Organization(name="Membership Org", slug=f"org-{uuid.uuid4().hex[:8]}")
    role = (await db_session.execute(select(Role).where(Role.name == "developer"))).scalar_one()

    db_session.add_all([user, org])
    await db_session.flush()

    m1 = OrganizationMember(organization_id=org.id, user_id=user.id, role_id=role.id, status="active")
    db_session.add(m1)
    await db_session.commit()

    m2 = OrganizationMember(organization_id=org.id, user_id=user.id, role_id=role.id, status="active")
    db_session.add(m2)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_duplicate_project_name_in_same_org_rejected(db_session: AsyncSession):
    """Composite unique constraint (organization_id, name) rejects duplicate project names in same org."""
    user = User(email="proj.owner@example.com", name="Proj Owner", password_hash="h")
    org = Organization(name="Project Org", slug=f"org-{uuid.uuid4().hex[:8]}")
    db_session.add_all([user, org])
    await db_session.flush()

    p1 = Project(organization_id=org.id, owner_id=user.id, name="Project Alpha")
    db_session.add(p1)
    await db_session.commit()

    # Same name in same org must fail
    p2 = Project(organization_id=org.id, owner_id=user.id, name="Project Alpha")
    db_session.add(p2)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_duplicate_role_name_and_permission_key_rejected(db_session: AsyncSession):
    """Role.name and Permission.key unique constraints reject duplicates."""
    r_dup = Role(name="owner", is_system=True)
    db_session.add(r_dup)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()

    p_dup = Permission(key="project.read", category="project")
    db_session.add(p_dup)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_duplicate_branch_in_same_repo_rejected(db_session: AsyncSession):
    """Composite unique constraint (repository_id, name) on branches rejects duplicates."""
    user = User(email="repo.owner@example.com", name="Repo Owner", password_hash="h")
    org = Organization(name="Git Org", slug=f"org-{uuid.uuid4().hex[:8]}")
    db_session.add_all([user, org])
    await db_session.flush()

    project = Project(organization_id=org.id, owner_id=user.id, name="Git Project")
    db_session.add(project)
    await db_session.flush()

    repo = Repository(
        project_id=project.id,
        provider="github",
        repository_url="https://github.com/org/backend-repo",
        status="connected",
    )
    db_session.add(repo)
    await db_session.flush()

    b1 = RepositoryBranch(repository_id=repo.id, name="main", is_default=True)
    db_session.add(b1)
    await db_session.commit()

    b2 = RepositoryBranch(repository_id=repo.id, name="main", is_default=False)
    db_session.add(b2)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()
