# ============================================================
# Project Service
# ============================================================

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import AuthorizationError, NotFoundError
from backend.app.repositories.project_repository import ProjectRepository
from backend.app.services.audit_service import AuditService


class ProjectService:
    """Project management business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ProjectRepository(db)
        self.audit = AuditService(db)

    async def create_project(
        self,
        *,
        name: str,
        description: str | None = None,
        language: str | None = None,
        default_branch: str | None = "main",
        owner_id: uuid.UUID,
        ip_address: str | None = None,
    ):
        """Create a new project."""
        project = await self.repo.create(
            name=name,
            description=description,
            language=language,
            default_branch=default_branch,
            owner_id=owner_id,
            created_by=owner_id,
        )
        await self.audit.log(
            user_id=owner_id,
            action="project.created",
            resource_type="project",
            resource_id=str(project.id),
            ip_address=ip_address,
        )
        return project

    async def get_project(self, project_id: uuid.UUID, user_id: uuid.UUID, role: str):
        """Get a single project with access check."""
        project = await self.repo.get_by_id(project_id)
        if project is None:
            raise NotFoundError(f"Project {project_id} not found")

        if role != "admin" and project.owner_id != user_id:
            raise AuthorizationError("You do not have access to this project")

        return project

    async def list_projects(
        self,
        user_id: uuid.UUID,
        role: str,
        *,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
    ):
        """List projects for a user."""
        if role == "admin":
            # Admins see all projects
            filters = []
            if search:
                from sqlalchemy import or_
                from backend.app.models.project import Project

                filters.append(
                    or_(
                        Project.name.ilike(f"%{search}%"),
                        Project.description.ilike(f"%{search}%"),
                    )
                )
            return await self.repo.get_all(
                page=page, page_size=page_size, filters=filters if filters else None
            )

        return await self.repo.get_user_projects(
            user_id, page=page, page_size=page_size, search=search
        )

    async def update_project(
        self,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        role: str,
        **kwargs,
    ):
        """Update a project with access check."""
        project = await self.get_project(project_id, user_id, role)

        # Filter out None values
        update_data = {k: v for k, v in kwargs.items() if v is not None}
        if not update_data:
            return project

        updated = await self.repo.update(project_id, **update_data)
        await self.audit.log(
            user_id=user_id,
            action="project.updated",
            resource_type="project",
            resource_id=str(project_id),
            metadata=update_data,
        )
        return updated

    async def delete_project(
        self,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        role: str,
    ):
        """Delete (archive) a project."""
        await self.get_project(project_id, user_id, role)
        await self.repo.update(project_id, is_archived=True)
        await self.audit.log(
            user_id=user_id,
            action="project.deleted",
            resource_type="project",
            resource_id=str(project_id),
        )
