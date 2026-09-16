# ============================================================
# Upload Service — File Upload, Validation, Storage
# ============================================================

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import get_settings
from backend.app.core.exceptions import NotFoundError, StorageError, ValidationError
from backend.app.core.logging import logger
from backend.app.repositories.upload_repository import UploadRepository
from backend.app.services.audit_service import AuditService
from backend.app.storage.service import StorageService
from backend.app.utils.file_utils import validate_file_extension, validate_file_size
from backend.app.utils.hashing import compute_sha256


class UploadService:
    """Handles file upload validation, safe storage via StorageService, and metadata."""

    def __init__(self, db: AsyncSession, storage: StorageService | None = None):
        self.db = db
        self.repo = UploadRepository(db)
        self.audit = AuditService(db)
        self.storage = storage or StorageService()
        self.settings = get_settings()

    async def upload_file(
        self,
        *,
        file: UploadFile,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
    ):
        """Validate, safely store, and record a file upload.

        Returns the Upload model instance.
        """
        # Sanitize filename - strip directory traversal
        raw_name = file.filename or "unknown"
        clean_name = Path(raw_name).name  # Strips any directory prefixes

        # 1. Validate extension
        validate_file_extension(clean_name, self.settings.allowed_extension_list)

        # 2. Read file content
        content = await file.read()

        # 3. Validate size
        validate_file_size(len(content), self.settings.max_upload_size_bytes)

        # 4. Compute hash
        sha256_hash = compute_sha256(content)

        # 5. Determine file type
        ext = Path(clean_name).suffix.lower()
        file_type = "zip" if ext == ".zip" else "single"

        # 6. Store file safely via StorageService (UUID generated path)
        upload_id = uuid.uuid4()
        stored_path = await self.storage.save_upload(
            project_id=project_id,
            upload_id=upload_id,
            file_extension=ext,
            content=content,
        )

        # 7. Create upload record
        upload = await self.repo.create(
            id=upload_id,
            project_id=project_id,
            user_id=user_id,
            original_name=clean_name,
            stored_path=str(stored_path),
            file_type=file_type,
            size_bytes=len(content),
            sha256_hash=sha256_hash,
            status="stored",
        )

        # 8. Audit log
        await self.audit.log(
            user_id=user_id,
            action="upload.created",
            resource_type="upload",
            resource_id=str(upload.id),
            metadata={
                "original_name": clean_name,
                "size_bytes": len(content),
                "file_type": file_type,
            },
        )

        logger.info(
            "File uploaded: {name} ({size} bytes) → {path}",
            name=clean_name,
            size=len(content),
            path=stored_path,
        )

        return upload

    async def get_upload(self, upload_id: uuid.UUID):
        """Get an upload by ID."""
        upload = await self.repo.get_by_id(upload_id)
        if upload is None:
            raise NotFoundError(f"Upload {upload_id} not found")
        return upload

    async def list_uploads(
        self, project_id: uuid.UUID, *, page: int = 1, page_size: int = 20
    ):
        """List uploads for a project."""
        return await self.repo.get_project_uploads(
            project_id, page=page, page_size=page_size
        )

    async def delete_upload(self, upload_id: uuid.UUID, user_id: uuid.UUID):
        """Delete an upload and its files via StorageService."""
        upload = await self.get_upload(upload_id)

        # Remove file from storage abstraction
        await self.storage.delete_file(upload.stored_path)

        await self.repo.delete(upload_id)
        await self.audit.log(
            user_id=user_id,
            action="upload.deleted",
            resource_type="upload",
            resource_id=str(upload_id),
        )
