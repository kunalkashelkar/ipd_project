# ============================================================
# Project Router — CRUD Operations
# ============================================================

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request

from backend.app.core.permissions import get_current_active_user, require_project_access
from backend.app.core.response import paginated_response, success_response
from backend.app.database.session import AsyncSession, get_db
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


@router.post("", summary="Create a new project")
async def create_project(
    body: ProjectCreate,
    request: Request,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new analysis project."""
    service = ProjectService(db)
    project = await service.create_project(
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


@router.get("", summary="List projects")
async def list_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = None,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List projects accessible to the user (with pagination)."""
    service = ProjectService(db)
    projects, total = await service.list_projects(
        user_id=current_user.id,
        role=current_user.role,
        page=page,
        page_size=page_size,
        search=search,
    )
    return paginated_response(
        items=[ProjectResponse.model_validate(p).model_dump(mode="json") for p in projects],
        total=total,
        page=page,
        page_size=page_size,
        message="Projects retrieved successfully",
    )


@router.get("/{project_id}", summary="Get project by ID")
async def get_project(
    project_id: uuid.UUID,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed project information."""
    service = ProjectService(db)
    project = await service.get_project(project_id, current_user.id, current_user.role)
    return success_response(
        data=ProjectResponse.model_validate(project).model_dump(mode="json"),
        message="Project retrieved successfully",
    )


@router.put("/{project_id}", summary="Update a project")
async def update_project(
    project_id: uuid.UUID,
    body: ProjectUpdate,
    current_user=Depends(require_project_access),
    db: AsyncSession = Depends(get_db),
):
    """Update project details."""
    service = ProjectService(db)
    # The dependency already checks access, but we pass role to the service as well
    project = await service.update_project(
        project_id,
        current_user.id,
        current_user.role,
        name=body.name,
        description=body.description,
        language=body.language,
        default_branch=body.default_branch,
        is_archived=body.is_archived,
    )
    return success_response(
        data=ProjectResponse.model_validate(project).model_dump(mode="json"),
        message="Project updated successfully",
    )


@router.delete("/{project_id}", summary="Delete a project")
async def delete_project(
    project_id: uuid.UUID,
    current_user=Depends(require_project_access),
    db: AsyncSession = Depends(get_db),
):
    """Archive a project (soft delete)."""
    service = ProjectService(db)
    await service.delete_project(project_id, current_user.id, current_user.role)
    return success_response(message="Project deleted successfully")
