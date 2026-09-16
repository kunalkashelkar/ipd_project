# ============================================================
# Scan Service
# ============================================================

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import ConflictError, NotFoundError, ValidationError
from backend.app.repositories.scan_repository import ScanRepository
from backend.app.repositories.upload_repository import UploadRepository
from backend.app.services.audit_service import AuditService


class ScanService:
    """Scan management business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.scan_repo = ScanRepository(db)
        self.upload_repo = UploadRepository(db)
        self.audit = AuditService(db)

    async def create_scan(
        self,
        *,
        project_id: uuid.UUID,
        source_snapshot_id: uuid.UUID | None = None,
        upload_id: uuid.UUID | None = None,
        repository_id: uuid.UUID | None = None,
        user_id: uuid.UUID,
    ):
        """Create a new scan and queue it for processing.

        Validates:
        - Either source_snapshot_id, upload_id, or repository_id must be provided
        - If source_snapshot_id is provided, it must belong to the project and be in READY status
        - No active scan already running for the project
        """
        if source_snapshot_id is None and upload_id is None and repository_id is None:
            raise ValidationError("Either source_snapshot_id, upload_id, or repository_id is required")

        # Check for active scans
        if await self.scan_repo.has_active_scan(project_id):
            raise ConflictError("Project already has an active scan")

        # Validate snapshot if provided
        if source_snapshot_id:
            from backend.app.models.source_snapshot import SourceSnapshot
            stmt = select(SourceSnapshot).where(SourceSnapshot.id == source_snapshot_id)
            res = await self.db.execute(stmt)
            snapshot = res.scalar_one_or_none()
            if snapshot is None or snapshot.project_id != project_id:
                raise NotFoundError(f"Snapshot {source_snapshot_id} not found in this project")
            if snapshot.status != "ready":
                raise ValidationError(
                    f"Cannot scan snapshot in '{snapshot.status}' state. Only READY snapshots can be scanned."
                )

        # Validate upload if provided
        if upload_id:
            upload = await self.upload_repo.get_by_id(upload_id)
            if upload is None:
                raise NotFoundError(f"Upload {upload_id} not found")
            if upload.project_id != project_id:
                raise ValidationError("Upload does not belong to this project")

        # Create scan
        scan = await self.scan_repo.create(
            project_id=project_id,
            source_snapshot_id=source_snapshot_id,
            upload_id=upload_id,
            repository_id=repository_id,
            created_by=user_id,
            status="pending",
            progress=0.0,
            current_stage="created",
        )

        # Audit
        await self.audit.log(
            user_id=user_id,
            action="scan.started",
            resource_type="scan",
            resource_id=str(scan.id),
            metadata={
                "project_id": str(project_id),
                "upload_id": str(upload_id) if upload_id else None,
            },
        )

        return scan

    async def get_scan(self, scan_id: uuid.UUID):
        """Get a scan by ID."""
        scan = await self.scan_repo.get_by_id(scan_id)
        if scan is None:
            raise NotFoundError(f"Scan {scan_id} not found")
        return scan

    async def get_scan_status(self, scan_id: uuid.UUID):
        """Get scan status (lightweight)."""
        return await self.get_scan(scan_id)

    async def list_scans(
        self,
        project_id: uuid.UUID | None = None,
        *,
        page: int = 1,
        page_size: int = 20,
    ):
        """List scans, optionally filtered by project."""
        if project_id:
            return await self.scan_repo.get_project_scans(
                project_id, page=page, page_size=page_size
            )
        return await self.scan_repo.get_all(page=page, page_size=page_size)

    async def cancel_scan(self, scan_id: uuid.UUID, user_id: uuid.UUID):
        """Cancel an active scan."""
        scan = await self.get_scan(scan_id)
        terminal_states = {"completed", "failed", "cancelled"}
        if scan.status in terminal_states:
            raise ConflictError(f"Scan is already in terminal state: {scan.status}")

        await self.scan_repo.update_status(
            scan_id,
            status="cancelled",
            error_message="Cancelled by user",
        )
        await self.audit.log(
            user_id=user_id,
            action="scan.cancelled",
            resource_type="scan",
            resource_id=str(scan_id),
        )
