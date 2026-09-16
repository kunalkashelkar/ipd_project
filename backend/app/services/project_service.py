# ============================================================
# Project Service (Phase 2 Tenant-Scoped)
# ============================================================

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import ConflictError, NotFoundError
from backend.app.models.project import Project
from backend.app.repositories.audit_repository import AuditRepository
from backend.app.repositories.project_repository import ProjectRepository


class ProjectService:
    """Project management business logic strictly scoped to Organizations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ProjectRepository(db)
        self.audit_repo = AuditRepository(db)

    async def create_project(
        self,
        *,
        org_id: uuid.UUID,
        name: str,
        description: str | None = None,
        language: str | None = None,
        default_branch: str | None = "main",
        owner_id: uuid.UUID,
        ip_address: str | None = None,
    ) -> Project:
        """Create a new project strictly scoped to the organization."""
        # Enforce uniqueness of active project names within the organization
        if await self.repo.check_name_exists_in_org(org_id, name):
            raise ConflictError(f"A project named '{name}' already exists in this organization")

        project = await self.repo.create(
            organization_id=org_id,
            name=name,
            description=description,
            language=language,
            default_branch=default_branch,
            owner_id=owner_id,
            created_by=owner_id,
        )

        await self.audit_repo.log_action(
            user_id=owner_id,
            organization_id=org_id,
            action="project.created",
            resource_type="project",
            resource_id=str(project.id),
            ip_address=ip_address,
            metadata={"name": name},
        )

        await self.db.commit()
        return project

    async def list_org_projects(
        self,
        org_id: uuid.UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
    ) -> tuple[list[Project], int]:
        """List projects belonging to the specified organization."""
        return await self.repo.get_org_projects(
            org_id=org_id,
            page=page,
            page_size=page_size,
            search=search,
        )

    async def update_project(
        self,
        *,
        project: Project,
        user_id: uuid.UUID,
        name: str | None = None,
        description: str | None = None,
        language: str | None = None,
        default_branch: str | None = None,
        is_archived: bool | None = None,
        ip_address: str | None = None,
    ) -> Project:
        """Update an existing project."""
        if name is not None and name != project.name:
            if await self.repo.check_name_exists_in_org(project.organization_id, name):
                raise ConflictError(f"A project named '{name}' already exists in this organization")
            project.name = name

        if description is not None:
            project.description = description
        if language is not None:
            project.language = language
        if default_branch is not None:
            project.default_branch = default_branch
        if is_archived is not None:
            project.is_archived = is_archived

        await self.audit_repo.log_action(
            user_id=user_id,
            organization_id=project.organization_id,
            action="project.updated",
            resource_type="project",
            resource_id=str(project.id),
            ip_address=ip_address,
        )

        await self.db.commit()
        return project

    async def delete_project(
        self,
        *,
        project: Project,
        user_id: uuid.UUID,
        ip_address: str | None = None,
    ) -> None:
        """Soft-delete (archive) a project to preserve scan and audit history."""
        project.is_archived = True

        await self.audit_repo.log_action(
            user_id=user_id,
            organization_id=project.organization_id,
            action="project.deleted",
            resource_type="project",
            resource_id=str(project.id),
            ip_address=ip_address,
        )

        await self.db.commit()
