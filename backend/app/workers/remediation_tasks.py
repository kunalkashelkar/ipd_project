# ============================================================
# Remediation, XAI & Validation Celery Worker Tasks (Phase 6)
# ============================================================

from __future__ import annotations

import uuid
from typing import Any

from loguru import logger
from sqlalchemy import select

from backend.app.database.session import async_session_factory
from backend.app.models.finding import Finding, FindingOccurrence
from backend.app.models.remediation import Remediation
from backend.app.models.source_snapshot import SourceFile, SourceSnapshot
from backend.app.services.remediation.contracts import RemediationRequest
from backend.app.services.remediation.provider import get_remediation_provider
from backend.app.services.remediation.validation_service import ValidationService
from backend.app.services.xai.service import XAIExplanationService
from backend.app.storage.service import StorageService
from backend.app.workers.base_task import AsyncCeleryTask
from backend.app.workers.celery_app import celery_app


@celery_app.task(bind=True, base=AsyncCeleryTask, name="generate_explanation_task")
async def generate_explanation_task(
    self,
    finding_id: str,
    method: str = "evidence_synthesizer",
    actor_id: str | None = None,
):
    """Asynchronously generate XAI explanation and attributions."""
    logger.info("Generating explanation for finding {id} using method {m}", id=finding_id, m=method)
    async with async_session_factory() as db:
        service = XAIExplanationService(db)
        await service.generate_explanation(
            finding_id=uuid.UUID(finding_id),
            method=method,
            actor_id=uuid.UUID(actor_id) if actor_id else None,
        )


@celery_app.task(bind=True, base=AsyncCeleryTask, name="generate_remediation_task")
async def generate_remediation_task(
    self,
    finding_id: str,
    provider_type: str | None = None,
    actor_id: str | None = None,
):
    """Asynchronously generate LLM remediation proposal."""
    logger.info("Generating remediation for finding {id}", id=finding_id)
    f_uuid = uuid.UUID(finding_id)
    a_uuid = uuid.UUID(actor_id) if actor_id else None

    async with async_session_factory() as db:
        finding = await db.get(Finding, f_uuid)
        if not finding:
            logger.error("Finding {id} not found for remediation", id=finding_id)
            return

        occ_stmt = (
            select(FindingOccurrence)
            .where(FindingOccurrence.finding_id == f_uuid)
            .order_by(FindingOccurrence.observed_at.desc())
            .limit(1)
        )
        occ_res = await db.execute(occ_stmt)
        occ = occ_res.scalar_one_or_none()
        if not occ:
            logger.error("Finding {id} has no occurrences", id=finding_id)
            return

        snapshot = await db.get(SourceSnapshot, occ.source_snapshot_id)
        if not snapshot:
            logger.error("Snapshot {id} not found", id=occ.source_snapshot_id)
            return

        # Determine next remediation number
        rem_stmt = (
            select(Remediation)
            .where(Remediation.finding_id == f_uuid)
            .order_by(Remediation.remediation_number.desc())
            .limit(1)
        )
        rem_res = await db.execute(rem_stmt)
        last_rem = rem_res.scalar_one_or_none()
        next_number = (last_rem.remediation_number + 1) if last_rem else 1

        # Read source code snippet from storage if available
        storage = StorageService()
        source_snippet = ""
        try:
            file_key = storage.snapshot_file_key(
                org_id=finding.organization_id,
                project_id=finding.project_id,
                snapshot_id=snapshot.id,
                relative_path=occ.file_path,
            )
            raw_bytes = await storage.backend.retrieve(file_key)
            source_snippet = raw_bytes.decode("utf-8", errors="replace")
        except Exception:
            source_snippet = f"# Code snippet for {occ.file_path} at line {occ.start_line}"

        # Build request
        req = RemediationRequest(
            finding_id=f_uuid,
            cwe_id=finding.cwe_id,
            vulnerability_type=finding.vulnerability_type,
            file_path=occ.file_path,
            function_name=occ.function_name,
            start_line=occ.start_line,
            end_line=occ.end_line,
            source_code_snippet=source_snippet[:2000],
        )

        provider = get_remediation_provider(provider_type)
        res = await provider.generate(req)

        # Store patch in object storage
        import hashlib
        checksum = hashlib.sha256(res.diff_content.encode("utf-8")).hexdigest()
        rem_id = uuid.uuid4()
        patch_key = storage.remediation_patch_key(
            org_id=finding.organization_id,
            project_id=finding.project_id,
            finding_id=finding.id,
            remediation_id=rem_id,
        )
        patch_uri = await storage.backend.store(res.diff_content.encode("utf-8"), patch_key)

        remediation = Remediation(
            id=rem_id,
            finding_id=finding.id,
            organization_id=finding.organization_id,
            project_id=finding.project_id,
            source_snapshot_id=snapshot.id,
            remediation_number=next_number,
            provider=res.provider,
            model_name=res.model_name,
            model_version=res.model_version,
            prompt_version=res.prompt_version,
            status="GENERATED",
            summary=res.summary,
            explanation=res.explanation,
            diff_content=res.diff_content,
            patch_artifact_uri=patch_uri,
            patch_checksum=checksum,
            changed_files=res.changed_files,
            confidence=res.confidence,
            warnings=res.warnings,
            generated_by_ai=True,
            is_active_candidate=True,
            created_by_user_id=a_uuid,
        )
        db.add(remediation)
        await db.commit()
        logger.info("Created remediation {id} for finding {fid}", id=rem_id, fid=finding_id)


@celery_app.task(bind=True, base=AsyncCeleryTask, name="execute_validation_task")
async def execute_validation_task(
    self,
    validation_id: str,
    actor_id: str | None = None,
):
    """Asynchronously execute multi-stage validation."""
    logger.info("Executing validation {id}", id=validation_id)
    v_uuid = uuid.UUID(validation_id)
    a_uuid = uuid.UUID(actor_id) if actor_id else None

    async with async_session_factory() as db:
        service = ValidationService(db)
        await service.execute_validation(v_uuid, actor_id=a_uuid)
