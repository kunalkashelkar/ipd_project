# ============================================================
# Repository VCS Repository — Data Access Layer (Phase 3)
# ============================================================

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.git_meta import RepositoryBranch, RepositoryCommit
from backend.app.models.repository import Repository


class RepositoryVcsRepository:
    """Encapsulates database operations for Repository, RepositoryBranch, and RepositoryCommit."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, repo_id: uuid.UUID) -> Repository | None:
        """Fetch repository by ID."""
        stmt = select(Repository).where(Repository.id == repo_id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def list_for_project(self, project_id: uuid.UUID) -> Sequence[Repository]:
        """List active repositories linked to a project."""
        stmt = (
            select(Repository)
            .where(Repository.project_id == project_id)
            .order_by(Repository.created_at.desc())
        )
        res = await self.db.execute(stmt)
        return res.scalars().all()

    async def find_existing(
        self, project_id: uuid.UUID, provider: str, repo_url: str
    ) -> Repository | None:
        """Find if this repository URL is already connected to the project."""
        stmt = select(Repository).where(
            Repository.project_id == project_id,
            Repository.provider == provider,
            Repository.repository_url == repo_url,
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def create_repository(
        self,
        project_id: uuid.UUID,
        provider: str,
        repository_url: str,
        branch: str = "main",
        auth_method: str | None = None,
    ) -> Repository:
        """Create new repository connection."""
        repo = Repository(
            id=uuid.uuid4(),
            project_id=project_id,
            provider=provider,
            repository_url=repository_url,
            branch=branch,
            auth_method=auth_method,
            status="connected",
        )
        self.db.add(repo)
        await self.db.commit()
        await self.db.refresh(repo)
        return repo

    async def list_branches(self, repo_id: uuid.UUID) -> Sequence[RepositoryBranch]:
        """List branches for a repository."""
        stmt = (
            select(RepositoryBranch)
            .where(RepositoryBranch.repository_id == repo_id)
            .order_by(RepositoryBranch.is_default.desc(), RepositoryBranch.name.asc())
        )
        res = await self.db.execute(stmt)
        return res.scalars().all()

    async def list_commits(self, repo_id: uuid.UUID, limit: int = 50) -> Sequence[RepositoryCommit]:
        """List commits for a repository."""
        stmt = (
            select(RepositoryCommit)
            .where(RepositoryCommit.repository_id == repo_id)
            .order_by(RepositoryCommit.committed_at.desc())
            .limit(limit)
        )
        res = await self.db.execute(stmt)
        return res.scalars().all()

    async def disconnect(self, repo_id: uuid.UUID) -> Repository | None:
        """Disconnect repository without deleting historical snapshots."""
        repo = await self.get_by_id(repo_id)
        if repo:
            repo.status = "disconnected"
            repo.disconnected_at = datetime.now(timezone.utc)
            await self.db.commit()
            await self.db.refresh(repo)
        return repo
