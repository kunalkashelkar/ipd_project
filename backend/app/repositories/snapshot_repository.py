# ============================================================
# Snapshot Repository — Data Access Layer (Phase 3)
# ============================================================

from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.source_snapshot import Function, SourceFile, SourceSnapshot


class SnapshotRepository:
    """Encapsulates database operations for SourceSnapshot, SourceFile, and Function."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, snapshot_id: uuid.UUID) -> SourceSnapshot | None:
        """Fetch snapshot by ID."""
        stmt = select(SourceSnapshot).where(SourceSnapshot.id == snapshot_id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def list_for_project(
        self, project_id: uuid.UUID, page: int = 1, page_size: int = 50
    ) -> tuple[Sequence[SourceSnapshot], int]:
        """List snapshots for a given project with pagination."""
        count_stmt = select(func.count(SourceSnapshot.id)).where(SourceSnapshot.project_id == project_id)
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = (
            select(SourceSnapshot)
            .where(SourceSnapshot.project_id == project_id)
            .order_by(SourceSnapshot.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        res = await self.db.execute(stmt)
        return res.scalars().all(), total

    async def list_files_for_snapshot(
        self,
        snapshot_id: uuid.UUID,
        page: int = 1,
        page_size: int = 50,
        search: str | None = None,
        language: str | None = None,
    ) -> tuple[Sequence[SourceFile], int]:
        """List source files in a snapshot with optional filtering."""
        query = select(SourceFile).where(SourceFile.source_snapshot_id == snapshot_id)
        count_query = select(func.count(SourceFile.id)).where(SourceFile.source_snapshot_id == snapshot_id)

        if search:
            like_term = f"%{search.strip()}%"
            query = query.where(SourceFile.relative_path.ilike(like_term))
            count_query = count_query.where(SourceFile.relative_path.ilike(like_term))

        if language:
            query = query.where(SourceFile.language == language.strip().lower())
            count_query = count_query.where(SourceFile.language == language.strip().lower())

        total = (await self.db.execute(count_query)).scalar() or 0

        stmt = (
            query.order_by(SourceFile.relative_path.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        res = await self.db.execute(stmt)
        return res.scalars().all(), total

    async def get_file_by_id(self, file_id: uuid.UUID) -> SourceFile | None:
        """Fetch single source file by ID."""
        stmt = select(SourceFile).where(SourceFile.id == file_id)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def list_functions_for_snapshot(
        self, snapshot_id: uuid.UUID, file_id: uuid.UUID | None = None
    ) -> Sequence[Function]:
        """List extracted functions for a snapshot."""
        stmt = (
            select(Function)
            .join(SourceFile, Function.source_file_id == SourceFile.id)
            .where(SourceFile.source_snapshot_id == snapshot_id)
        )
        if file_id:
            stmt = stmt.where(Function.source_file_id == file_id)

        stmt = stmt.order_by(Function.start_line.asc())
        res = await self.db.execute(stmt)
        return res.scalars().all()
