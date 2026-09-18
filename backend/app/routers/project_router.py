# ============================================================
# Phase 2 Project Router — Tenant-Scoped CRUD
# ============================================================

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Request, status

from backend.app.core.authorization import (
    get_current_user,
    require_permission,
    require_project_access,
    resolve_organization_context,
)
from backend.app.core.exceptions import AuthorizationError
from backend.app.core.response import paginated_response, success_response
from backend.app.database.session import AsyncSession, get_db
from backend.app.models.organization import Organization, OrganizationMember
from backend.app.models.project import Project
from backend.app.models.user import User
from backend.app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate
from backend.app.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["Projects"])


def _get_client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


@router.post("", summary="Create a new project", status_code=status.HTTP_201_CREATED)
async def create_project(
    body: ProjectCreate,
    request: Request,
    org_context: tuple[Organization, OrganizationMember] = Depends(require_permission("project.create")),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new project strictly scoped to the active Organization."""
    org, _ = org_context
    service = ProjectService(db)
    project = await service.create_project(
        org_id=org.id,
        name=body.name,
        description=body.description,
        language=body.language,
        default_branch=body.default_branch,
        owner_id=current_user.id,
        ip_address=_get_client_ip(request),
    )
    return success_response(
        data=ProjectResponse.model_validate(project).model_dump(mode="json"),
        message="Project created successfully",
        status_code=201,
    )


@router.get("", summary="List projects in organization")
async def list_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = None,
    org_context: tuple[Organization, OrganizationMember] = Depends(require_permission("project.read")),
    db: AsyncSession = Depends(get_db),
):
    """List projects accessible to the authenticated member in their organization."""
    org, _ = org_context
    service = ProjectService(db)
    projects, total = await service.list_org_projects(
        org_id=org.id,
        page=page,
        page_size=page_size,
        search=search,
    )
    return paginated_response(
        items=[ProjectResponse.model_validate(p).model_dump(mode="json") for p in projects],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{project_id}", summary="Get a project by ID")
async def get_project(
    project_id: str,
    project_context: tuple[Project, OrganizationMember] = Depends(require_project_access),
):
    """Retrieve project details ensuring tenant isolation."""
    project, member = project_context
    return success_response(
        data=ProjectResponse.model_validate(project).model_dump(mode="json"),
        message="Project retrieved successfully",
    )


@router.patch("/{project_id}", summary="Update a project")
async def update_project(
    project_id: str,
    body: ProjectUpdate,
    request: Request,
    project_context: tuple[Project, OrganizationMember] = Depends(require_project_access),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update project details (requires project.update permission)."""
    project, member = project_context

    # Verify project.update permission on member role
    if member.role.name != "owner":
        granted_keys = {rp.permission.key for rp in member.role.permissions if rp.permission}
        if "project.update" not in granted_keys:
            raise AuthorizationError("Insufficient permissions to update project")

    service = ProjectService(db)
    updated = await service.update_project(
        project=project,
        user_id=current_user.id,
        name=body.name,
        description=body.description,
        language=body.language,
        default_branch=body.default_branch,
        is_archived=body.is_archived,
        ip_address=_get_client_ip(request),
    )
    return success_response(
        data=ProjectResponse.model_validate(updated).model_dump(mode="json"),
        message="Project updated successfully",
    )


@router.delete("/{project_id}", summary="Delete (archive) a project")
async def delete_project(
    project_id: str,
    request: Request,
    project_context: tuple[Project, OrganizationMember] = Depends(require_project_access),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Archive a project (requires project.delete permission)."""
    project, member = project_context

    if member.role.name != "owner":
        granted_keys = {rp.permission.key for rp in member.role.permissions if rp.permission}
        if "project.delete" not in granted_keys:
            raise AuthorizationError("Insufficient permissions to archive project")

    service = ProjectService(db)
    await service.delete_project(
        project=project,
        user_id=current_user.id,
        ip_address=_get_client_ip(request),
    )
    return success_response(message="Project archived successfully")


@router.post("/{project_id}/archive", summary="Archive a project")
async def archive_project(
    project_id: str,
    request: Request,
    project_context: tuple[Project, OrganizationMember] = Depends(require_project_access),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Archive or unarchive a project to freeze/unfreeze actions while preserving historical audit and scan provenance."""
    project, member = project_context

    if member.role.name != "owner":
        granted_keys = {rp.permission.key for rp in member.role.permissions if rp.permission}
        if "project.delete" not in granted_keys:
            raise AuthorizationError("Insufficient permissions to archive project")

    project.is_archived = not project.is_archived
    if project.is_archived:
        project.archived_at = datetime.now(timezone.utc)
    else:
        project.archived_at = None

    await db.commit()
    await db.refresh(project)
    return success_response(data=project, message="Project archive status updated")
