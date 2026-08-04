# ============================================================
# Projects Router — CRUD placeholder
# ============================================================

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter

from backend.app.schemas import ProjectCreate, ProjectListResponse, ProjectResponse

router = APIRouter(prefix="/projects", tags=["Projects"])

# ── In-memory store (placeholder until DB is wired in Phase 2) ──
_projects: dict[uuid.UUID, ProjectResponse] = {}


@router.get(
    "",
    response_model=ProjectListResponse,
    summary="List projects",
    description="Returns all projects. Currently returns in-memory data.",
)
async def list_projects() -> ProjectListResponse:
    projects = list(_projects.values())
    return ProjectListResponse(projects=projects, total=len(projects))


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=201,
    summary="Create a project",
    description="Creates a new project entry.",
)
async def create_project(body: ProjectCreate) -> ProjectResponse:
    now = datetime.now(timezone.utc)
    project = ProjectResponse(
        id=uuid.uuid4(),
        name=body.name,
        description=body.description,
        status="created",
        created_at=now,
        updated_at=now,
    )
    _projects[project.id] = project
    return project


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Get a project",
    description="Returns a single project by ID.",
)
async def get_project(project_id: uuid.UUID) -> ProjectResponse:
    from fastapi import HTTPException

    project = _projects.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project
