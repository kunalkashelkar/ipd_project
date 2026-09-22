# ============================================================
# Scan Service — Phase 4 Core Service Layer
# ============================================================

from __future__ import annotations

import json
import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.core.exceptions import (
    BadRequestError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from backend.app.models.analysis_artifact import AnalysisArtifact
from backend.app.models.project import Project
from backend.app.models.scan import Scan, ScanEvent, ScanStageRun
from backend.app.models.source_snapshot import SourceSnapshot
from backend.app.repositories.scan_repository import ScanRepository
from backend.app.repositories.upload_repository import UploadRepository
from backend.app.services.audit_service import AuditService
from backend.app.services.scan_lifecycle.lifecycle_service import ScanLifecycleService
from backend.app.services.scan_lifecycle.state_machine import ScanStage
from backend.app.storage.service import StorageService


class ScanService:
    """Scan management business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.scan_repo = ScanRepository(db)
        self.upload_repo = UploadRepository(db)
        self.audit = AuditService(db)
        self.lifecycle = ScanLifecycleService(db)
        self.storage = StorageService()

    async def create_scan(
        self,
        *,
        project_id: uuid.UUID,
        source_snapshot_id: str | uuid.UUID | None = None,
        upload_id: str | uuid.UUID | None = None,
        repository_id: str | uuid.UUID | None = None,
        user_id: uuid.UUID,
        idempotency_key: str | None = None,
        config: dict[str, Any] | None = None,
    ) -> Scan:
        """Create a new scan and queue it for asynchronous processing.

        Enforces:
        - Idempotency deduplication when idempotency_key is provided
        - Immutable SourceSnapshot binding (must belong to project & be READY)
        - Tenant boundary and single active scan concurrency guard
        """
        # 1. Idempotency check: if key already exists, return existing scan
        if idempotency_key:
            stmt_idem = select(Scan).where(Scan.idempotency_key == idempotency_key)
            res_idem = await self.db.execute(stmt_idem)
            existing_scan = res_idem.scalar_one_or_none()
            if existing_scan:
                return existing_scan

        # 2. Validate source targets
        if source_snapshot_id is None and upload_id is None and repository_id is None:
            raise ValidationError("A source snapshot, upload, or repository is required to start a scan")

        # Resolve project to ensure it exists and get organization_id
        stmt_proj = select(Project).where(Project.id == project_id)
        res_proj = await self.db.execute(stmt_proj)
        project = res_proj.scalar_one_or_none()
        if not project:
            raise NotFoundError(f"Project {project_id} not found")

        # Guard against duplicate concurrent active scans on the same project
        if await self.scan_repo.has_active_scan(project_id):
            raise ConflictError("Project already has an active scan running")

        # 3. Validate immutable snapshot
        resolved_snapshot_id: uuid.UUID | None = None
        snapshot: SourceSnapshot | None = None
        if source_snapshot_id:
            from backend.app.core.identifiers import is_valid_uuid
            from sqlalchemy import or_

            snap_str = str(source_snapshot_id).strip()
            if is_valid_uuid(snap_str):
                cond = or_(SourceSnapshot.id == uuid.UUID(snap_str), SourceSnapshot.public_id == snap_str)
            else:
                cond = (SourceSnapshot.public_id == snap_str)

            stmt_snap = select(SourceSnapshot).where(cond)
            res_snap = await self.db.execute(stmt_snap)
            snapshot = res_snap.scalar_one_or_none()
            if snapshot is None or snapshot.project_id != project_id:
                raise NotFoundError(f"Snapshot {source_snapshot_id} not found in this project")
            if snapshot.status != "ready":
                raise ValidationError(
                    f"Cannot scan snapshot in '{snapshot.status}' state. Only READY snapshots can be scanned."
                )
            resolved_snapshot_id = snapshot.id

        resolved_upload_id: uuid.UUID | None = None
        if upload_id:
            from backend.app.core.identifiers import is_valid_uuid

            up_str = str(upload_id).strip()
            if is_valid_uuid(up_str):
                resolved_upload_id = uuid.UUID(up_str)
            else:
                raise ValidationError(f"Invalid upload_id: {upload_id}")

        resolved_repository_id: uuid.UUID | None = None
        if repository_id:
            from backend.app.core.identifiers import is_valid_uuid

            repo_str = str(repository_id).strip()
            if is_valid_uuid(repo_str):
                resolved_repository_id = uuid.UUID(repo_str)
            else:
                raise ValidationError(f"Invalid repository_id: {repository_id}")

        # 4. Create scan entity
        scan = Scan(
            id=uuid.uuid4(),
            project_id=project_id,
            organization_id=project.organization_id,
            source_snapshot_id=resolved_snapshot_id,
            upload_id=resolved_upload_id,
            repository_id=resolved_repository_id,
            created_by=user_id,
            status="queued",
            progress=5.0,
            current_stage="queued",
            stage_attempt=1,
            retry_count=0,
            timeout_seconds=config.get("timeout_seconds", 1800) if config else 1800,
            config=config or {},
            idempotency_key=idempotency_key,
        )
        self.db.add(scan)
        await self.db.commit()
        await self.db.refresh(scan)

        scan.project_name = project.name
        scan.project_public_id = project.public_id
        if resolved_snapshot_id and snapshot:
            scan.source_snapshot_version = snapshot.source_version
            scan.source_snapshot_public_id = snapshot.public_id

        # 5. Insert initial stage run & event records
        initial_run = ScanStageRun(
            scan_id=scan.id,
            stage="queued",
            attempt=1,
            status="completed",
            duration_seconds=0.0,
            stage_metadata={"created_by": str(user_id)},
        )
        self.db.add(initial_run)

        initial_event = ScanEvent(
            scan_id=scan.id,
            event_type="scan.queued",
            stage="queued",
            payload={"source_snapshot_id": str(resolved_snapshot_id) if resolved_snapshot_id else None},
        )
        self.db.add(initial_event)
        await self.db.commit()

        # 6. Audit log
        await self.audit.log(
            user_id=user_id,
            action="scan.started",
            resource_type="scan",
            resource_id=str(scan.id),
            metadata={
                "project_id": str(project_id),
                "source_snapshot_id": str(resolved_snapshot_id) if resolved_snapshot_id else None,
            },
        )

        # 7. Enqueue Celery orchestration task
        from backend.app.workers.scan_tasks import orchestrate_scan

        orchestrate_scan.delay(str(scan.id))

        return scan

    async def get_scan(self, scan_id: uuid.UUID) -> Scan:
        """Get full details of a scan."""
        stmt = (
            select(Scan)
            .where(Scan.id == scan_id)
            .options(
                selectinload(Scan.stage_runs),
                selectinload(Scan.artifacts),
                selectinload(Scan.source_snapshot),
                selectinload(Scan.project),
            )
        )
        res = await self.db.execute(stmt)
        scan = res.scalar_one_or_none()
        if scan is None:
            raise NotFoundError(f"Scan {scan_id} not found")
        scan.project_name = scan.project.name if scan.project else None
        scan.project_public_id = scan.project.public_id if scan.project else None
        scan.source_snapshot_version = (
            scan.source_snapshot.source_version if scan.source_snapshot else None
        )
        scan.source_snapshot_public_id = (
            scan.source_snapshot.public_id if scan.source_snapshot else None
        )
        return scan

    async def get_scan_status(self, scan_id: uuid.UUID) -> Scan:
        """Get lightweight scan status for polling."""
        stmt = select(Scan).where(Scan.id == scan_id)
        res = await self.db.execute(stmt)
        scan = res.scalar_one_or_none()
        if scan is None:
            raise NotFoundError(f"Scan {scan_id} not found")
        return scan

    async def list_scans(
        self,
        project_id: uuid.UUID | None = None,
        organization_id: uuid.UUID | None = None,
        status: str | None = None,
        *,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Scan], int]:
        """List scans filtered by project, status, and/or organization."""
        from backend.app.models.finding import FindingOccurrence

        stmt = (
            select(Scan)
            .join(Project, Scan.project_id == Project.id)
            .options(
                selectinload(Scan.project),
                selectinload(Scan.source_snapshot),
            )
            .order_by(Scan.created_at.desc())
        )
        count_stmt = select(func.count(Scan.id)).join(Project, Scan.project_id == Project.id)

        if organization_id is not None:
            stmt = stmt.where(Project.organization_id == organization_id)
            count_stmt = count_stmt.where(Project.organization_id == organization_id)

        if project_id is not None:
            stmt = stmt.where(Scan.project_id == project_id)
            count_stmt = count_stmt.where(Scan.project_id == project_id)

        if status:
            stmt = stmt.where(func.lower(Scan.status) == status.lower().strip())
            count_stmt = count_stmt.where(func.lower(Scan.status) == status.lower().strip())

        res_total = await self.db.execute(count_stmt)
        total = res_total.scalar() or 0

        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)
        res = await self.db.execute(stmt)
        scans = list(res.scalars().all())

        if scans:
            scan_ids = [s.id for s in scans]
            finding_counts_stmt = (
                select(
                    FindingOccurrence.scan_id,
                    func.count(func.distinct(FindingOccurrence.finding_id)),
                )
                .where(FindingOccurrence.scan_id.in_(scan_ids))
                .group_by(FindingOccurrence.scan_id)
            )
            fc_res = await self.db.execute(finding_counts_stmt)
            counts_map = dict(fc_res.all())

            for s in scans:
                s.finding_count = counts_map.get(s.id, 0)
                s.project_name = s.project.name if s.project else None
                s.project_public_id = s.project.public_id if s.project else None
                s.source_snapshot_version = (
                    s.source_snapshot.source_version if s.source_snapshot else None
                )
                s.source_snapshot_public_id = (
                    s.source_snapshot.public_id if s.source_snapshot else None
                )
                if not hasattr(s, "purpose") or not s.purpose:
                    s.purpose = "GENERAL_SCAN"

        return scans, total

    async def get_scan_stages(self, scan_id: uuid.UUID) -> list[ScanStageRun]:
        """Retrieve execution history of all stages for a scan."""
        stmt = (
            select(ScanStageRun)
            .where(ScanStageRun.scan_id == scan_id)
            .order_by(ScanStageRun.created_at.asc(), ScanStageRun.attempt.asc())
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def get_scan_artifacts(self, scan_id: uuid.UUID) -> list[AnalysisArtifact]:
        """Retrieve all canonical analysis artifacts generated for a scan.
        
        Truthfulness enforcement: If PDG was produced under native fallback with 0 edges
        or marked unsupported, ensure its status is explicitly 'unsupported' with metadata explanation.
        """
        stmt = (
            select(AnalysisArtifact)
            .where(AnalysisArtifact.scan_id == scan_id)
            .order_by(AnalysisArtifact.created_at.asc())
        )
        res = await self.db.execute(stmt)
        artifacts = list(res.scalars().all())
        for art in artifacts:
            if art.artifact_type == "PDG" and (
                art.status == "unsupported"
                or (art.tool_name == "native_ast_analyzer" and art.edge_count == 0)
            ):
                art.status = "unsupported"
                note_text = (
                    "Program Dependence Graph (PDG) generation requires the Joern analysis backend. "
                    "The current native analyzer does not provide control/data-dependence analysis."
                )
                if art.artifact_metadata is None:
                    art.artifact_metadata = {}
                if isinstance(art.artifact_metadata, dict):
                    art.artifact_metadata.setdefault("note", note_text)
                    art.artifact_metadata.setdefault("engine_fallback", True)
        return artifacts

    async def get_artifact_detail(self, scan_id: uuid.UUID, artifact_id: uuid.UUID) -> tuple[AnalysisArtifact, str]:
        """Retrieve artifact and its presigned download URL."""
        stmt = select(AnalysisArtifact).where(
            AnalysisArtifact.id == artifact_id, AnalysisArtifact.scan_id == scan_id
        )
        res = await self.db.execute(stmt)
        artifact = res.scalar_one_or_none()
        if not artifact:
            raise NotFoundError(f"Artifact {artifact_id} not found for scan {scan_id}")

        if artifact.status == "unsupported" or (
            artifact.artifact_type == "PDG"
            and (artifact.tool_name == "native_ast_analyzer" and artifact.edge_count == 0)
        ):
            raise BadRequestError(
                "Program Dependence Graph (PDG) is unsupported under the native AST analyzer fallback. "
                "Download URL cannot be generated."
            )

        download_url = await self.storage.generate_download_url(artifact.artifact_uri, expires_in_seconds=3600)
        return artifact, download_url

    async def get_artifact_content(self, scan_id: uuid.UUID, artifact_id: uuid.UUID) -> tuple[AnalysisArtifact, bytes]:
        """Retrieve artifact record and raw content bytes from storage for safe direct download."""
        stmt = select(AnalysisArtifact).where(
            AnalysisArtifact.id == artifact_id, AnalysisArtifact.scan_id == scan_id
        )
        res = await self.db.execute(stmt)
        artifact = res.scalar_one_or_none()
        if not artifact:
            raise NotFoundError(f"Artifact {artifact_id} not found for scan {scan_id}")

        if artifact.status == "unsupported" or (
            artifact.artifact_type == "PDG"
            and (artifact.tool_name == "native_ast_analyzer" and artifact.edge_count == 0)
        ):
            raise BadRequestError(
                "Program Dependence Graph (PDG) is unsupported under the native AST analyzer fallback. "
                "Download is not available."
            )

        content_bytes = await self.storage.read_file(artifact.artifact_uri)
        return artifact, content_bytes

    async def get_taint_evidence(self, scan_id: uuid.UUID) -> dict[str, Any]:
        """Retrieve structured taint evidence payload for a scan."""
        stmt = select(AnalysisArtifact).where(
            AnalysisArtifact.scan_id == scan_id, AnalysisArtifact.artifact_type == "TAINT"
        )
        res = await self.db.execute(stmt)
        taint_art = res.scalar_one_or_none()
        if not taint_art:
            return {
                "status": "not_run",
                "message": "Taint analysis was not executed for this scan.",
                "paths": [],
                "source_count": 0,
                "sink_count": 0,
            }

        if taint_art.status == "failed":
            return {
                "status": "failed",
                "message": taint_art.error_message or "Taint analysis execution failed.",
                "paths": [],
                "source_count": 0,
                "sink_count": 0,
            }

        try:
            content_bytes = await self.storage.read_file(taint_art.artifact_uri)
            data = json.loads(content_bytes.decode("utf-8"))
            data["status"] = "ready"
            return data
        except Exception as err:
            return {
                "status": "failed",
                "message": f"Failed to load taint evidence payload: {str(err)}",
                "metadata": taint_art.artifact_metadata or {},
                "paths": [],
                "source_count": taint_art.node_count,
            }

    async def cancel_scan(self, scan_id: uuid.UUID, user_id: uuid.UUID) -> Scan:
        """Cancel an active scan."""
        scan = await self.lifecycle.cancel_scan(scan_id, user_id=user_id)
        await self.audit.log(
            user_id=user_id,
            action="scan.cancelled",
            resource_type="scan",
            resource_id=str(scan_id),
        )
        return scan

    async def retry_scan(self, scan_id: uuid.UUID, user_id: uuid.UUID) -> Scan:
        """Retry a failed or timed out scan."""
        scan = await self.lifecycle.retry_scan(scan_id)
        from backend.app.workers.scan_tasks import orchestrate_scan

        orchestrate_scan.delay(str(scan.id))
        await self.audit.log(
            user_id=user_id,
            action="scan.retried",
            resource_type="scan",
            resource_id=str(scan_id),
        )
        return scan
