# ============================================================
# Upload Repository
# ============================================================

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.upload import Upload
from backend.app.repositories.base import BaseRepository


class UploadRepository(BaseRepository[Upload]):
    """Repository for Upload model operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, Upload)

    async def get_project_uploads(
        self,
        project_id: uuid.UUID,
        *,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Upload], int]:
        """Get uploads for a project."""
        return await self.get_all(
            page=page,
            page_size=page_size,
            filters=[Upload.project_id == project_id],
            order_by=Upload.created_at.desc(),
        )

    async def update_status(
        self, upload_id: uuid.UUID, status: str, error_message: str | None = None
    ) -> Upload | None:
        """Update upload status."""
        return await self.update(
            upload_id, status=status, error_message=error_message
        )
