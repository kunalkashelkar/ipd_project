# ============================================================
# Repository Router — VCS Connection, Branching, and Sync (Phase 3)
# ============================================================

from __future__ import annotations

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.authorization import get_current_user, resolve_active_organization
from backend.app.core.response import paginated_response, success_response
from backend.app.database.session import get_db
from backend.app.models.project import Project
from backend.app.models.user import User
from backend.app.repositories.project_repository import ProjectRepository
from backend.app.repositories.repository_vcs_repository import RepositoryVcsRepository
from backend.app.schemas.snapshot_schemas import (
    BranchResponse,
    CommitResponse,
    RepositoryConnectRequest,
    RepositoryResponse,
)
from backend.app.services.vcs import get_vcs_provider
from backend.app.workers.repository_tasks import sync_repository_task

router = APIRouter(tags=["Repositories"])


async def _resolve_authorized_project(
    project_id: uuid.UUID,
    db: AsyncSession,
    current_user: User,
    active_org_id: uuid.UUID,
) -> Project:
    """Ensure project belongs strictly to active organization."""
    project_repo = ProjectRepository(db)
    project = await project_repo.get_by_id(project_id)
    if not project or project.organization_id != active_org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found in active organization",
        )
    return project


@router.post(
    "/projects/{project_id}/repositories",
    status_code=status.HTTP_201_CREATED,
)
async def connect_repository(
    project_id: uuid.UUID,
    req: RepositoryConnectRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    active_org_id: uuid.UUID = Depends(resolve_active_organization),
):
    """Connect a Git or GitHub repository to a project with automated branch discovery and commit synchronization."""
    project = await _resolve_authorized_project(project_id, db, current_user, active_org_id)
    repo_vcs_repo = RepositoryVcsRepository(db)

    # Prevent duplicate connections for the same repository url
    existing = await repo_vcs_repo.find_existing(project.id, req.provider, req.repository_url)
    if existing:
        if existing.status == "disconnected":
            existing.status = "connected"
            existing.branch = req.branch
            await db.commit()
            sync_repository_task.delay(str(existing.id), req.branch, req.auth_token)
            return success_response(
                data=RepositoryResponse.model_validate(existing).model_dump(mode="json"),
                message="Repository re-connected and sync initiated",
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Repository is already connected to this project",
        )

    # Validate remote connection
    provider = get_vcs_provider(req.provider)
    try:
        is_valid = await provider.validate_connection(req.repository_url, req.auth_token)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not reach or authenticate with the specified repository. Ensure it is public or provide a valid access token.",
            )
    except HTTPException:
        raise
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to validate repository connection: {exc}",
        )

    # Resolve tracking branch
    target_branch = (req.branch or "").strip()
    if not target_branch:
        try:
            target_branch = await provider.get_default_branch(req.repository_url, req.auth_token)
        except Exception:
            target_branch = "main"
    else:
        # Validate that the explicitly specified branch exists
        try:
            available_branches = await provider.list_branches(req.repository_url, req.auth_token)
            if available_branches and target_branch not in available_branches:
                branch_list_str = ", ".join(available_branches[:8])
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Branch '{target_branch}' not found on remote repository. Available branches: {branch_list_str}",
                )
        except HTTPException:
            raise
        except Exception as branch_err:
            from loguru import logger
            logger.warning("Could not verify branch list: {err}", err=branch_err)

    try:
        repo = await repo_vcs_repo.create_repository(
            project_id=project.id,
            provider=req.provider,
            repository_url=req.repository_url,
            branch=target_branch,
            auth_method="token" if req.auth_token else "none",
        )
    except Exception as db_exc:
        from loguru import logger
        logger.error("Failed to persist repository record for project {pid}: {err}", pid=project.id, err=db_exc)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to connect this repository right now. Please try again.",
        )

    # Enqueue background sync only after repository record is safely committed
    sync_repository_task.delay(str(repo.id), target_branch, req.auth_token)

    return success_response(
        data=RepositoryResponse.model_validate(repo).model_dump(mode="json"),
        message="Repository connected and sync queued",
        status_code=201,
    )


@router.get(
    "/projects/{project_id}/repositories",
)
async def list_repositories(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    active_org_id: uuid.UUID = Depends(resolve_active_organization),
):
    """List connected repositories for a project."""
    await _resolve_authorized_project(project_id, db, current_user, active_org_id)
    repo_vcs_repo = RepositoryVcsRepository(db)
    items = await repo_vcs_repo.list_for_project(project_id)
    return success_response(
        data=[RepositoryResponse.model_validate(r).model_dump(mode="json") for r in items]
    )


@router.get(
    "/projects/{project_id}/repositories/{repo_id}",
)
async def get_repository_detail(
    project_id: uuid.UUID,
    repo_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    active_org_id: uuid.UUID = Depends(resolve_active_organization),
):
    """Get connected repository details."""
    await _resolve_authorized_project(project_id, db, current_user, active_org_id)
    repo_vcs_repo = RepositoryVcsRepository(db)
    repo = await repo_vcs_repo.get_by_id(repo_id)
    if not repo or repo.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")
    return success_response(
        data=RepositoryResponse.model_validate(repo).model_dump(mode="json")
    )


@router.get(
    "/repositories/{repo_id}/branches",
)
@router.get(
    "/projects/{project_id}/repositories/{repo_id}/branches",
)
async def list_repository_branches(
    repo_id: uuid.UUID,
    project_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    active_org_id: uuid.UUID = Depends(resolve_active_organization),
):
    """List tracked and remote branches for a repository."""
    repo_vcs_repo = RepositoryVcsRepository(db)
    repo = await repo_vcs_repo.get_by_id(repo_id)
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")
    await _resolve_authorized_project(repo.project_id, db, current_user, active_org_id)

    branches = await repo_vcs_repo.list_branches(repo_id)
    if branches:
        return success_response(
            data=[
                BranchResponse(
                    name=b.name,
                    is_default=b.is_default,
                    head_commit_sha=b.head_commit_sha,
                ).model_dump(mode="json")
                for b in branches
            ]
        )

    # Fallback to remote discovery
    try:
        provider = get_vcs_provider(repo.provider)
        branch_names = await provider.list_branches(repo.repository_url or "")
        return success_response(
            data=[
                BranchResponse(
                    name=name,
                    is_default=(name == repo.branch),
                ).model_dump(mode="json")
                for name in branch_names
            ]
        )
    except Exception:
        return success_response(
            data=[BranchResponse(name=repo.branch or "main", is_default=True).model_dump(mode="json")]
        )


@router.post(
    "/repositories/{repo_id}/branches/select",
)
async def select_repository_branch(
    repo_id: uuid.UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    active_org_id: uuid.UUID = Depends(resolve_active_organization),
):
    """Select the active tracking branch for a repository."""
    branch_name = body.get("branch_name") or body.get("branch")
    if not branch_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="branch_name required")

    repo_vcs_repo = RepositoryVcsRepository(db)
    repo = await repo_vcs_repo.get_by_id(repo_id)
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")

    await _resolve_authorized_project(repo.project_id, db, current_user, active_org_id)
    repo.branch = branch_name
    await db.commit()
    await db.refresh(repo)
    return success_response(
        data=RepositoryResponse.model_validate(repo).model_dump(mode="json"),
        message=f"Tracking branch set to {branch_name}",
    )


@router.get(
    "/repositories/{repo_id}/commits",
)
@router.get(
    "/projects/{project_id}/repositories/{repo_id}/commits",
)
async def list_repository_commits(
    repo_id: uuid.UUID,
    project_id: uuid.UUID | None = None,
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    active_org_id: uuid.UUID = Depends(resolve_active_organization),
):
    """List historical imported commits for a repository."""
    repo_vcs_repo = RepositoryVcsRepository(db)
    repo = await repo_vcs_repo.get_by_id(repo_id)
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")

    await _resolve_authorized_project(repo.project_id, db, current_user, active_org_id)
    commits = await repo_vcs_repo.list_commits(repo_id, limit=limit)
    return paginated_response(
        items=[CommitResponse.model_validate(c).model_dump(mode="json") for c in commits],
        total=len(commits),
        page=1,
        page_size=limit,
    )


@router.post(
    "/projects/{project_id}/repositories/{repo_id}/sync",
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_repository_sync(
    project_id: uuid.UUID,
    repo_id: uuid.UUID,
    branch: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    active_org_id: uuid.UUID = Depends(resolve_active_organization),
):
    """Trigger background repository synchronization, creating a new immutable snapshot."""
    await _resolve_authorized_project(project_id, db, current_user, active_org_id)
    repo_vcs_repo = RepositoryVcsRepository(db)
    repo = await repo_vcs_repo.get_by_id(repo_id)
    if not repo or repo.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")

    target_branch = branch or repo.branch or "main"
    sync_repository_task.delay(str(repo.id), target_branch)

    return success_response(
        data={"repository_id": str(repo.id), "branch": target_branch},
        message="Repository sync initiated",
        status_code=202,
    )


@router.post(
    "/projects/{project_id}/repositories/{repo_id}/disconnect",
)
async def disconnect_repository(
    project_id: uuid.UUID,
    repo_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    active_org_id: uuid.UUID = Depends(resolve_active_organization),
):
    """Disconnect repository connection while preserving all historical snapshots for audit and scan provenance."""
    await _resolve_authorized_project(project_id, db, current_user, active_org_id)
    repo_vcs_repo = RepositoryVcsRepository(db)
    repo = await repo_vcs_repo.get_by_id(repo_id)
    if not repo or repo.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")

    updated = await repo_vcs_repo.disconnect(repo_id)
    return success_response(
        data=RepositoryResponse.model_validate(updated).model_dump(mode="json"),
        message="Repository disconnected successfully",
    )
