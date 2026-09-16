# ============================================================
# Project Repository (Phase 2 Tenant-Scoped)
# ============================================================

from __future__ import annotations

import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.project import Project
from backend.app.repositories.base import BaseRepository


class ProjectRepository(BaseRepository[Project]):
    """Repository for Project model operations strictly scoped to an Organization."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, Project)

    async def get_by_org_and_id(self, org_id: uuid.UUID, project_id: uuid.UUID) -> Project | None:
        """Fetch project ensuring it belongs to the specified organization."""
        stmt = select(Project).where(
            Project.id == project_id,
            Project.organization_id == org_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_org_projects(
        self,
        org_id: uuid.UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        include_archived: bool = False,
    ) -> tuple[list[Project], int]:
        """Get projects belonging to an organization with optional search."""
        filters = [Project.organization_id == org_id]

        if not include_archived:
            filters.append(Project.is_archived == False)  # noqa: E712

        if search:
            filters.append(
                or_(
                    Project.name.ilike(f"%{search}%"),
                    Project.description.ilike(f"%{search}%"),
                )
            )

        return await self.get_all(
            page=page,
            page_size=page_size,
            filters=filters,
            order_by=Project.created_at.desc(),
        )

    async def check_name_exists_in_org(self, org_id: uuid.UUID, name: str) -> bool:
        """Check if active project with name already exists in the organization."""
        stmt = select(Project.id).where(
            Project.organization_id == org_id,
            Project.name == name,
            Project.is_archived == False,  # noqa: E712
        )
        result = await self.db.execute(stmt)
        return result.first() is not None
