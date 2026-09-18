# ============================================================
# Snapshot Router — Immutable Source Ingestion & Inspection (Phase 3)
# ============================================================

from __future__ import annotations

import io
import uuid
import zipfile
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.authorization import get_current_user, resolve_active_organization
from backend.app.core.exceptions import StorageError
from backend.app.core.response import paginated_response, success_response
from backend.app.database.session import get_db
from backend.app.models.project import Project
from backend.app.models.source_snapshot import SourceSnapshot
from backend.app.models.user import User
from backend.app.repositories.project_repository import ProjectRepository
from backend.app.repositories.snapshot_repository import SnapshotRepository
from backend.app.schemas.snapshot_schemas import (
    FunctionResponse,
    SourceFileContentResponse,
    SourceFileResponse,
    SourceSnapshotResponse,
)
from backend.app.services.code_parser import sanitize_relative_path
from backend.app.storage.service import StorageService
from backend.app.workers.snapshot_tasks import process_source_snapshot_task

router = APIRouter(tags=["Snapshots & Sources"])


async def _resolve_authorized_project(
    project_id: str | uuid.UUID,
    db: AsyncSession,
    current_user: User,
    active_org_id: uuid.UUID,
) -> Project:
    """Ensure project belongs strictly to active organization."""
    project_repo = ProjectRepository(db)
    project = await project_repo.get_by_org_and_id_or_public_id(active_org_id, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found in active organization",
        )
    return project


@router.post(
    "/projects/{project_id}/snapshots/upload",
    status_code=status.HTTP_201_CREATED,
)
@router.post(
    "/projects/{project_id}/sources/upload",
    status_code=status.HTTP_201_CREATED,
)
async def upload_source_archive(
    project_id: str,
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    active_org_id: uuid.UUID = Depends(resolve_active_organization),
):
    """Upload a source code ZIP archive and start asynchronous preprocessing."""
    project = await _resolve_authorized_project(project_id, db, current_user, active_org_id)

    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Filename required")

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")

    if not zipfile.is_zipfile(io.BytesIO(content)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is not a valid ZIP archive",
        )

    storage = StorageService()
    snapshot_id = uuid.uuid4()
    archive_key = StorageService.snapshot_archive_key(
        org_id=active_org_id, project_id=project.id, snapshot_id=snapshot_id, ext=".zip"
    )

    await storage.save_object(content, archive_key)

    snapshot = SourceSnapshot(
        id=snapshot_id,
        project_id=project.id,
        source_type="upload",
        source_version=file.filename,
        content_hash=str(snapshot_id),
        artifact_uri=archive_key,
        status="pending",
        file_count=0,
        total_bytes=len(content),
        created_by=current_user.id,
        preprocessing_version="v1.0.0",
    )
    db.add(snapshot)
    await db.commit()
    await db.refresh(snapshot)

    # Enqueue isolated worker preprocessing task
    process_source_snapshot_task.delay(
        str(snapshot.id),
        str(active_org_id),
        str(project.id),
    )

    return success_response(
        data=SourceSnapshotResponse.model_validate(snapshot).model_dump(mode="json"),
        message="Source archive uploaded successfully",
        status_code=201,
    )


@router.post(
    "/projects/{project_id}/snapshots/files",
    status_code=status.HTTP_201_CREATED,
)
@router.post(
    "/projects/{project_id}/sources/files",
    status_code=status.HTTP_201_CREATED,
)
async def upload_source_files(
    project_id: str,
    files: List[UploadFile],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    active_org_id: uuid.UUID = Depends(resolve_active_organization),
):
    """Upload one or multiple individual source files as a single coherent snapshot."""
    project = await _resolve_authorized_project(project_id, db, current_user, active_org_id)

    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one file required")

    zip_buffer = io.BytesIO()
    total_bytes = 0
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            raw_name = f.filename or "unknown_source.txt"
            try:
                clean_name = sanitize_relative_path(raw_name)
            except ValueError:
                clean_name = Path(raw_name).name
            file_content = await f.read()
            total_bytes += len(file_content)
            zf.writestr(clean_name, file_content)

    zip_bytes = zip_buffer.getvalue()
    storage = StorageService()
    snapshot_id = uuid.uuid4()
    archive_key = StorageService.snapshot_archive_key(
        org_id=active_org_id, project_id=project.id, snapshot_id=snapshot_id, ext=".zip"
    )
    await storage.save_object(zip_bytes, archive_key)

    snapshot = SourceSnapshot(
        id=snapshot_id,
        project_id=project.id,
        source_type="upload",
        source_version=f"{len(files)} files uploaded",
        content_hash=str(snapshot_id),
        artifact_uri=archive_key,
        status="pending",
        file_count=len(files),
        total_bytes=total_bytes,
        created_by=current_user.id,
        preprocessing_version="v1.0.0",
    )
    db.add(snapshot)
    await db.commit()
    await db.refresh(snapshot)

    process_source_snapshot_task.delay(
        str(snapshot.id),
        str(active_org_id),
        str(project.id),
    )

    return success_response(
        data=SourceSnapshotResponse.model_validate(snapshot).model_dump(mode="json"),
        message="Source files uploaded successfully",
        status_code=201,
    )


@router.get(
    "/projects/{project_id}/snapshots",
)
async def list_project_snapshots(
    project_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    active_org_id: uuid.UUID = Depends(resolve_active_organization),
):
    """List immutable source snapshots for a project."""
    project = await _resolve_authorized_project(project_id, db, current_user, active_org_id)
    repo = SnapshotRepository(db)
    items, total = await repo.list_for_project(project.id, page=page, page_size=page_size)
    return paginated_response(
        items=[SourceSnapshotResponse.model_validate(i).model_dump(mode="json") for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/projects/{project_id}/snapshots/{snapshot_id}",
)
async def get_snapshot_detail(
    project_id: str,
    snapshot_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    active_org_id: uuid.UUID = Depends(resolve_active_organization),
):
    """Get metadata for a specific snapshot."""
    project = await _resolve_authorized_project(project_id, db, current_user, active_org_id)
    repo = SnapshotRepository(db)
    snapshot = await repo.get_by_id_or_public_id(snapshot_id)
    if not snapshot or snapshot.project_id != project.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Snapshot not found")
    return success_response(
        data=SourceSnapshotResponse.model_validate(snapshot).model_dump(mode="json")
    )


@router.get(
    "/projects/{project_id}/snapshots/{snapshot_id}/files",
)
async def list_snapshot_files(
    project_id: str,
    snapshot_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    search: str | None = Query(None),
    language: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    active_org_id: uuid.UUID = Depends(resolve_active_organization),
):
    """List source files in an immutable snapshot."""
    project = await _resolve_authorized_project(project_id, db, current_user, active_org_id)
    repo = SnapshotRepository(db)
    snapshot = await repo.get_by_id_or_public_id(snapshot_id)
    if not snapshot or snapshot.project_id != project.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Snapshot not found")

    items, total = await repo.list_files_for_snapshot(
        snapshot_id=snapshot.id,
        page=page,
        page_size=page_size,
        search=search,
        language=language,
    )
    return paginated_response(
        items=[SourceFileResponse.model_validate(i).model_dump(mode="json") for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/projects/{project_id}/snapshots/{snapshot_id}/files/{file_id}/content",
)
async def get_source_file_content(
    project_id: str,
    snapshot_id: str,
    file_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    active_org_id: uuid.UUID = Depends(resolve_active_organization),
):
    """Safely retrieve source file content from object storage for in-browser inspection."""
    project = await _resolve_authorized_project(project_id, db, current_user, active_org_id)
    repo = SnapshotRepository(db)
    snapshot = await repo.get_by_id_or_public_id(snapshot_id)
    if not snapshot or snapshot.project_id != project.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Snapshot not found")

    sf = await repo.get_file_by_id(file_id)
    if not sf or sf.source_snapshot_id != snapshot.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source file not found")

    if sf.is_binary:
        return success_response(
            data=SourceFileContentResponse(
                relative_path=sf.relative_path,
                content="[Binary File — preview not available]",
                language=sf.language,
                line_count=0,
                size_bytes=sf.size_bytes,
                is_binary=True,
            ).model_dump(mode="json")
        )

    storage = StorageService()
    try:
        raw_bytes = await storage.read_file(sf.original_artifact_uri)
        content_str = raw_bytes.decode(sf.encoding or "utf-8", errors="replace")
        return success_response(
            data=SourceFileContentResponse(
                relative_path=sf.relative_path,
                content=content_str,
                language=sf.language,
                line_count=sf.line_count,
                size_bytes=sf.size_bytes,
                is_binary=False,
            ).model_dump(mode="json")
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read file from storage: {exc}",
        )


@router.get(
    "/projects/{project_id}/snapshots/{snapshot_id}/functions",
)
async def list_snapshot_functions(
    project_id: str,
    snapshot_id: str,
    file_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    active_org_id: uuid.UUID = Depends(resolve_active_organization),
):
    """List extracted functions for a snapshot."""
    project = await _resolve_authorized_project(project_id, db, current_user, active_org_id)
    repo = SnapshotRepository(db)
    snapshot = await repo.get_by_id_or_public_id(snapshot_id)
    if not snapshot or snapshot.project_id != project.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Snapshot not found")

    funcs = await repo.list_functions_for_snapshot(snapshot_id=snapshot.id, file_id=file_id)
    return paginated_response(
        items=[FunctionResponse.model_validate(f).model_dump(mode="json") for f in funcs],
        total=len(funcs),
        page=1,
        page_size=len(funcs) or 50,
    )
