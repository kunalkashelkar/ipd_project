# ============================================================
# Project Repository
# ============================================================

from __future__ import annotations

import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.project import Project
from backend.app.repositories.base import BaseRepository


class ProjectRepository(BaseRepository[Project]):
    """Repository for Project model operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, Project)

    async def get_user_projects(
        self,
        user_id: uuid.UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        include_archived: bool = False,
    ) -> tuple[list[Project], int]:
        """Get projects owned by a user with optional search."""
        filters = [Project.owner_id == user_id]

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
