# ============================================================
# Pytest Configuration & Test Fixtures (Phase 2 Multi-Tenant)
# ============================================================

import asyncio
import os
import uuid
from typing import AsyncGenerator
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Set test environment
os.environ["APP_ENV"] = "test"
os.environ["SECRET_KEY"] = "test-secret-key-32-bytes-long-super-safe"
os.environ["STORAGE_BACKEND"] = "local"
os.environ["LOCAL_STORAGE_PATH"] = "./storage_test"

from backend.app.core.config import get_settings
from backend.app.core.security import create_token_pair, hash_password
from backend.app.database.base import Base
from backend.app.database.session import get_db
from backend.app.main import app
from backend.app.models.organization import Organization, OrganizationMember
from backend.app.models.rbac import Permission, Role, RolePermission
from backend.app.models.user import User

# Test Database: In-memory SQLite with async support
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
test_session_factory = async_sessionmaker(
    bind=test_engine, class_=AsyncSession, expire_on_commit=False
)


async def seed_test_rbac(session: AsyncSession) -> dict[str, Role]:
    """Seed baseline roles and permissions in test database."""
    role_names = ["owner", "admin", "security_analyst", "developer", "viewer"]
    roles = {}
    for name in role_names:
        r = Role(name=name, description=f"{name} role", is_system=True)
        session.add(r)
        roles[name] = r

    # Permissions
    perm_keys = [
        ("organization.read", "organization"),
        ("organization.update", "organization"),
        ("team.read", "team"),
        ("team.invite", "team"),
        ("team.remove", "team"),
        ("team.role.update", "team"),
        ("project.read", "project"),
        ("project.create", "project"),
        ("project.update", "project"),
        ("project.delete", "project"),
        ("repository.read", "repository"),
        ("scan.read", "scan"),
        ("scan.create", "scan"),
        ("finding.read", "finding"),
        ("finding.update", "finding"),
        ("finding.assign", "finding"),
        ("finding.suppress", "finding"),
        ("finding.accept_risk", "finding"),
        ("api_key.read", "api_key"),
        ("api_key.create", "api_key"),
        ("api_key.revoke", "api_key"),
        ("audit.read", "audit"),
    ]

    perms = {}
    for k, cat in perm_keys:
        p = Permission(key=k, description=k, category=cat)
        session.add(p)
        perms[k] = p

    await session.flush()

    # Mappings
    mappings = {
        "owner": [k for k, _ in perm_keys],
        "admin": [k for k, _ in perm_keys],
        "security_analyst": [
            "organization.read", "team.read", "project.read", "repository.read",
            "scan.read", "scan.create", "finding.read", "finding.update",
            "finding.assign", "finding.suppress", "finding.accept_risk", "audit.read"
        ],
        "developer": ["organization.read", "team.read", "project.read", "repository.read", "scan.read", "scan.create", "finding.read"],
        "viewer": ["organization.read", "team.read", "project.read", "repository.read", "scan.read", "finding.read"],
    }

    for role_name, granted in mappings.items():
        role = roles[role_name]
        for g in granted:
            rp = RolePermission(role_id=role.id, permission_id=perms[g].id)
            session.add(rp)

    await session.flush()
    return roles


@pytest.fixture(scope="session")
def event_loop():
    """Create a session-scoped event loop."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a clean in-memory database session for each test with seeded RBAC."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with test_session_factory() as session:
        await seed_test_rbac(session)
        await session.commit()
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Provide an HTTP test client overriding the database session."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a standard test user with their own organization where they are Owner."""
    user = User(
        name="Test Researcher",
        email="researcher@example.com",
        password_hash=hash_password("password123"),
        role="researcher",
        status="active",
        is_verified=True,
    )
    db_session.add(user)
    await db_session.flush()

    org = Organization(name="Researcher Org", slug=f"researcher-org-{uuid.uuid4().hex[:6]}")
    db_session.add(org)
    await db_session.flush()

    stmt = select(Role).where(Role.name == "owner")
    res = await db_session.execute(stmt)
    owner_role = res.scalar_one()

    member = OrganizationMember(
        organization_id=org.id,
        user_id=user.id,
        role_id=owner_role.id,
        status="active",
    )
    db_session.add(member)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user: User) -> dict[str, str]:
    """Generate authorization headers for the standard test user."""
    tokens = create_token_pair(str(test_user.id), test_user.email)
    return {"Authorization": f"Bearer {tokens['access_token']}"}
