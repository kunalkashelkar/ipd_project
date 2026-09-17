# ============================================================
# Upload Router — File Uploads & Processing
# ============================================================

from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Query, UploadFile, status

from backend.app.core.authorization import get_current_user, require_project_access
from backend.app.core.exceptions import AuthorizationError
from backend.app.core.response import paginated_response, success_response
from backend.app.database.session import AsyncSession, get_db
from backend.app.models.user import User
from backend.app.schemas.upload import UploadResponse
from backend.app.services.preprocessing_service import PreprocessingService
from backend.app.services.upload_service import UploadService

router = APIRouter(prefix="/uploads", tags=["Uploads"])


@router.post("", summary="Upload a file for a project", status_code=status.HTTP_201_CREATED)
async def upload_file(
    project_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a source code file or ZIP archive."""
    project, member = await require_project_access(project_id, current_user, db)

    if member.role.name != "owner":
        granted = {rp.permission.key for rp in member.role.permissions if rp.permission}
        if "project.update" not in granted and "scan.create" not in granted:
            raise AuthorizationError("Permission denied: Action requires 'project.update' or 'scan.create'")

    service = UploadService(db)
    upload = await service.upload_file(
        file=file,
        project_id=project_id,
        user_id=current_user.id,
    )
    return success_response(
        data=UploadResponse.model_validate(upload).model_dump(mode="json"),
        message="File uploaded successfully",
        status_code=201,
    )


@router.get("", summary="List uploads for a project")
async def list_uploads(
    project_id: uuid.UUID = Query(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all uploads for a specific project."""
    await require_project_access(project_id, current_user, db)

    service = UploadService(db)
    uploads, total = await service.list_uploads(
        project_id, page=page, page_size=page_size
    )
    return paginated_response(
        items=[UploadResponse.model_validate(u).model_dump(mode="json") for u in uploads],
        total=total,
        page=page,
        page_size=page_size,
        message="Uploads retrieved successfully",
    )


@router.get("/{upload_id}", summary="Get upload by ID")
async def get_upload(
    upload_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get metadata for a specific upload."""
    service = UploadService(db)
    upload = await service.get_upload(upload_id)

    # Check project access
    await require_project_access(upload.project_id, current_user, db)

    return success_response(
        data=UploadResponse.model_validate(upload).model_dump(mode="json"),
        message="Upload retrieved successfully",
    )


@router.delete("/{upload_id}", summary="Delete an upload")
async def delete_upload(
    upload_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete an upload and its associated files from storage."""
    service = UploadService(db)
    upload = await service.get_upload(upload_id)

    project, member = await require_project_access(upload.project_id, current_user, db)

    if member.role.name != "owner":
        granted = {rp.permission.key for rp in member.role.permissions if rp.permission}
        if "project.update" not in granted and "project.delete" not in granted:
            raise AuthorizationError("Permission denied: Action requires 'project.update' or 'project.delete'")

    await service.delete_upload(upload_id, current_user.id)
    return success_response(message="Upload deleted successfully")


@router.post("/{upload_id}/process", summary="Trigger preprocessing (Sync for MVP)")
async def process_upload(
    upload_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger the preprocessing pipeline for an upload."""
    upload_service = UploadService(db)
    upload = await upload_service.get_upload(upload_id)
    project, member = await require_project_access(upload.project_id, current_user, db)

    if member.role.name != "owner":
        granted = {rp.permission.key for rp in member.role.permissions if rp.permission}
        if "project.update" not in granted and "scan.create" not in granted:
            raise AuthorizationError("Permission denied: Action requires 'project.update' or 'scan.create'")

    from backend.app.repositories.upload_repository import UploadRepository
    repo = UploadRepository(db)
    await repo.update_status(upload_id, "processing")

    def _run_preprocessing(upload_path: str, u_id: str):
        preprocessor = PreprocessingService()
        try:
            preprocessor.process_upload(upload_path, u_id)
            from backend.app.core.logging import logger
            logger.info("Preprocessing complete for {u_id}", u_id=u_id)
        except Exception as e:
            from backend.app.core.logging import logger
            logger.error("Preprocessing failed for {u_id}: {err}", u_id=u_id, err=str(e))

    background_tasks.add_task(_run_preprocessing, upload.stored_path, str(upload_id))
    return success_response(message="Preprocessing initiated")
