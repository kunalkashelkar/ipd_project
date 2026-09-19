# ============================================================
# Report Service (Phase 7 — Authoritative Asynchronous Reports)
# ============================================================

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any, Sequence

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.core.exceptions import AuthorizationError, NotFoundError, ValidationError
from backend.app.models.report import Report, ReportFile
from backend.app.repositories.project_repository import ProjectRepository
from backend.app.repositories.report_repository import ReportRepository
from backend.app.repositories.scan_repository import ScanRepository
from backend.app.services.audit_service import AuditService
from backend.app.services.report_generator import ReportDataCollector, ReportGenerator
from backend.app.storage.service import StorageService


class ReportService:
    """Authoritative business logic for asynchronous security report generation."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.report_repo = ReportRepository(db)
        self.scan_repo = ScanRepository(db)
        self.project_repo = ProjectRepository(db)
        self.audit = AuditService(db)
        self.storage = StorageService()

    async def get_scan_reports(
        self,
        scan_id: uuid.UUID,
        *,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[Sequence[Report], int]:
        """Get paginated reports for a scan."""
        scan = await self.scan_repo.get_by_id(scan_id)
        if not scan:
            raise NotFoundError(f"Scan {scan_id} not found")

        return await self.report_repo.get_scan_reports(
            scan_id, page=page, page_size=page_size
        )

    async def list_reports(
        self,
        org_id: uuid.UUID,
        *,
        project_id: uuid.UUID | None = None,
        scan_id: uuid.UUID | None = None,
        report_type: str | None = None,
        format: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[Sequence[Report], int]:
        """List reports scoped to an organization."""
        return await self.report_repo.get_org_reports(
            org_id,
            project_id=project_id,
            scan_id=scan_id,
            report_type=report_type,
            format=format,
            status=status,
            page=page,
            page_size=page_size,
        )

    async def get_report(
        self, report_id_or_public_id: str | uuid.UUID, org_id: uuid.UUID
    ) -> Report:
        """Get report details enforcing organization boundary."""
        report = await self.report_repo.get_by_id_or_public_id(report_id_or_public_id)
        if not report or report.organization_id != org_id:
            raise NotFoundError("Report not found")
        return report

    async def request_report(
        self,
        scan_id: str | uuid.UUID,
        format: str,
        report_type: str,
        user_id: uuid.UUID,
        org_id: uuid.UUID,
        config: dict[str, Any] | None = None,
    ) -> Report:
        """Enqueue asynchronous report generation."""
        scan = await self.scan_repo.get_by_id_or_public_id(scan_id)
        if not scan:
            raise NotFoundError(f"Scan {scan_id} not found")

        project = await self.project_repo.get_by_id(scan.project_id)
        if not project or project.organization_id != org_id:
            raise NotFoundError(f"Scan {scan_id} does not belong to active organization")

        clean_fmt = format.lower().strip()
        if clean_fmt not in ("pdf", "html", "json", "csv"):
            raise ValidationError(f"Invalid format '{format}'. Supported formats: pdf, html, json, csv")

        clean_type = report_type.lower().strip()
        if clean_type not in ("developer", "security", "executive"):
            clean_type = "security"

        report = await self.report_repo.create(
            scan_id=scan.id,
            project_id=project.id,
            organization_id=org_id,
            created_by=user_id,
            report_type=clean_type,
            format=clean_fmt,
            status="queued",
            config=config,
        )

        await self.audit.log(
            user_id=user_id,
            action="report.requested",
            resource_type="report",
            resource_id=str(report.id),
            metadata={"public_id": report.public_id, "format": clean_fmt, "type": clean_type},
        )

        await self.db.commit()

        # Enqueue background generation task
        from backend.app.workers.report_tasks import generate_report_task
        try:
            generate_report_task.delay(str(report.id))
        except Exception as queue_err:
            logger.warning("Could not dispatch Celery task directly: {err}", err=queue_err)

        report.files = []
        return report

    async def execute_generation(self, report_id: uuid.UUID) -> Report:
        """Generate report content, upload artifact to MinIO/S3, and update status."""
        report = await self.report_repo.get_by_id_or_public_id(report_id)
        if not report:
            raise NotFoundError(f"Report {report_id} not found")

        try:
            # 1. Transition to generating
            report.status = "generating"
            await self.db.commit()

            # 2. Collect authoritative data
            collector = ReportDataCollector(self.db)
            data = await collector.collect(report.scan_id)

            # 3. Generate artifact bytes
            generator = ReportGenerator()
            content_bytes, content_type = generator.generate(
                data, report_type=report.report_type, format=report.format
            )

            # 4. Compute SHA256 checksum and size
            checksum = hashlib.sha256(content_bytes).hexdigest()
            size_bytes = len(content_bytes)

            # 5. Save to object storage
            storage_key = StorageService.report_file_key(
                org_id=report.organization_id or uuid.uuid4(),
                project_id=report.project_id or uuid.uuid4(),
                report_public_id=report.public_id,
                format=report.format,
            )
            await self.storage.save_object(content_bytes, storage_key)

            # 6. Record ReportFile
            report_file = ReportFile(
                id=uuid.uuid4(),
                report_id=report.id,
                format=report.format,
                storage_key=storage_key,
                content_type=content_type,
                size_bytes=size_bytes,
                checksum_sha256=checksum,
            )
            self.db.add(report_file)
            report.files.append(report_file)

            # 7. Complete Report
            report.status = "completed"
            report.file_path = storage_key
            report.generated_at = datetime.now(timezone.utc)
            report.error_message = None
            await self.db.commit()

            logger.info(
                "Report {pid} ({fmt}, {type}) successfully generated and stored at {key}",
                pid=report.public_id,
                fmt=report.format,
                type=report.report_type,
                key=storage_key,
            )

            # 8. Send notification if creator exists
            if report.created_by:
                from backend.app.services.notification_service import NotificationService
                notif_svc = NotificationService(self.db)
                await notif_svc.create_notification(
                    user_id=report.created_by,
                    type="report_ready",
                    title=f"Report ready: {report.report_type.capitalize()} ({report.format.upper()})",
                    body=f"Your requested {report.report_type} report for scan {data.get('scan', {}).get('public_id', '')} has completed.",
                    organization_id=report.organization_id,
                    entity_type="report",
                    entity_id=report.id,
                    severity="info",
                    link_url=f"/reports",
                )

            # Reload report with files eagerly loaded
            final_res = await self.db.execute(
                select(Report).options(selectinload(Report.files)).where(Report.id == report.id)
            )
            return final_res.scalar_one()

        except Exception as exc:
            logger.error("Failed to generate report {rid}: {err}", rid=report_id, err=exc)
            await self.db.rollback()
            refetched = await self.report_repo.get_by_id(report_id)
            if refetched:
                refetched.status = "failed"
                refetched.error_message = str(exc)
                await self.db.commit()
            raise

    async def get_report_download(
        self, report_id_or_public_id: str | uuid.UUID, org_id: uuid.UUID
    ) -> tuple[bytes, str, str]:
        """Retrieve report content bytes, filename, and content type."""
        report = await self.get_report(report_id_or_public_id, org_id)
        if report.status != "completed" or not report.files:
            raise ValidationError(f"Report is not ready for download (current status: '{report.status}')")

        report_file = report.files[0]
        content_bytes = await self.storage.read_file(report_file.storage_key)
        filename = f"{report.public_id}_{report.report_type}.{report.format}"
        return content_bytes, filename, report_file.content_type
