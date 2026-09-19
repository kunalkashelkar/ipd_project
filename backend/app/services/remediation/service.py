# ============================================================
# Remediation Service — Business Logic & Lifecycle (Phase 6)
# ============================================================
# Orchestrates remediation generation, human review, patch security,
# and triggers isolated validation attempts.
# ============================================================

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any

from loguru import logger
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.core.exceptions import NotFoundError, ValidationError
from backend.app.models.finding import Finding, FindingOccurrence
from backend.app.models.remediation import Remediation, RemediationValidation
from backend.app.models.source_snapshot import SourceSnapshot
from backend.app.services.audit_service import AuditService
from backend.app.services.remediation.contracts import RemediationRequest
from backend.app.services.remediation.patch_service import PatchService
from backend.app.services.remediation.provider import get_remediation_provider
from backend.app.services.remediation.validation_service import ValidationService
from backend.app.storage.service import StorageService


class RemediationService:
    """Core domain service for proposed remediations and validation management."""

    def __init__(self, db: AsyncSession, storage: StorageService | None = None):
        self.db = db
        self.storage = storage or StorageService()
        self.audit = AuditService(db)

    async def generate_remediation(
        self,
        *,
        finding_id: uuid.UUID,
        organization_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
        provider_type: str | None = None,
        prompt_version: str = "v1.0.0",
    ) -> Remediation:
        """Generate a proposed remediation with secure patch provenance."""
        finding = await self.db.get(Finding, finding_id)
        if not finding or finding.organization_id != organization_id:
            raise NotFoundError(f"Finding '{finding_id}' not found.")

        occ_stmt = (
            select(FindingOccurrence)
            .where(FindingOccurrence.finding_id == finding_id)
            .order_by(desc(FindingOccurrence.observed_at))
            .limit(1)
        )
        occ_res = await self.db.execute(occ_stmt)
        occ = occ_res.scalar_one_or_none()
        if not occ:
            raise ValidationError(f"Finding '{finding_id}' has no recorded occurrences.")

        snapshot = await self.db.get(SourceSnapshot, occ.source_snapshot_id)
        if not snapshot:
            raise NotFoundError(f"Snapshot '{occ.source_snapshot_id}' not found.")

        # Determine attempt sequence number
        num_stmt = (
            select(Remediation)
            .where(Remediation.finding_id == finding_id)
            .order_by(desc(Remediation.remediation_number))
            .limit(1)
        )
        num_res = await self.db.execute(num_stmt)
        last_rem = num_res.scalar_one_or_none()
        next_number = (last_rem.remediation_number + 1) if last_rem else 1

        # Attempt to load exact source context from storage
        source_snippet = ""
        try:
            file_key = self.storage.snapshot_file_key(
                org_id=organization_id,
                project_id=finding.project_id,
                snapshot_id=snapshot.id,
                relative_path=occ.file_path,
            )
            raw_bytes = await self.storage.backend.retrieve(file_key)
            source_snippet = raw_bytes.decode("utf-8", errors="replace")
        except Exception:
            source_snippet = f"# Source code for {occ.file_path} at line {occ.start_line}"

        # Construct safe prompt/context request
        req = RemediationRequest(
            finding_id=finding.id,
            cwe_id=finding.cwe_id,
            vulnerability_type=finding.vulnerability_type,
            file_path=occ.file_path,
            function_name=occ.function_name,
            start_line=occ.start_line,
            end_line=occ.end_line,
            source_code_snippet=source_snippet[:4000],
        )

        provider = get_remediation_provider(provider_type)
        res = await provider.generate(req)

        # Validate patch security before persisting
        PatchService.validate_patch_security(res.diff_content)

        # Calculate checksum and store in object storage
        checksum = hashlib.sha256(res.diff_content.encode("utf-8")).hexdigest()
        rem_id = uuid.uuid4()
        patch_key = self.storage.remediation_patch_key(
            org_id=organization_id,
            project_id=finding.project_id,
            finding_id=finding.id,
            remediation_id=rem_id,
        )
        patch_uri = await self.storage.backend.store(res.diff_content.encode("utf-8"), patch_key)

        remediation = Remediation(
            id=rem_id,
            finding_id=finding.id,
            organization_id=organization_id,
            project_id=finding.project_id,
            source_snapshot_id=snapshot.id,
            remediation_number=next_number,
            provider=res.provider,
            model_name=res.model_name,
            model_version=res.model_version,
            prompt_version=prompt_version,
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
            created_by_user_id=user_id,
        )

        # If previous candidates existed, update their is_active_candidate flag
        prev_stmt = select(Remediation).where(
            Remediation.finding_id == finding.id,
            Remediation.id != rem_id,
            Remediation.is_active_candidate.is_(True),
        )
        prev_res = await self.db.execute(prev_stmt)
        for prev in prev_res.scalars().all():
            prev.is_active_candidate = False

        self.db.add(remediation)
        await self.db.commit()
        await self.db.refresh(remediation)

        await self.audit.log(
            user_id=user_id,
            action="remediation_generated",
            resource_type="remediation",
            resource_id=str(remediation.id),
            metadata={
                "finding_id": str(finding.id),
                "remediation_number": next_number,
                "provider": res.provider,
                "checksum": checksum,
            },
        )
        await self.db.commit()

        if user_id:
            try:
                from backend.app.services.notification_service import NotificationService
                notif = NotificationService(self.db)
                await notif.notify_fix_ready(
                    finding_id=finding.id,
                    finding_public_id=finding.public_id,
                    user_id=user_id,
                    organization_id=organization_id,
                    remediation_id=remediation.id,
                )
                await self.db.commit()
            except Exception as e:
                logger.warning("Failed to emit fix_ready notification: {err}", err=e)

        return remediation

    async def review_remediation(
        self,
        *,
        remediation_id: uuid.UUID,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        decision: str,
        comment: str | None = None,
    ) -> Remediation:
        """Approve or reject a proposed remediation."""
        remediation = await self.db.get(Remediation, remediation_id)
        if not remediation or remediation.organization_id != organization_id:
            raise NotFoundError(f"Remediation '{remediation_id}' not found.")

        decision_upper = decision.upper()
        if decision_upper not in ("APPROVE", "REJECT"):
            raise ValidationError("Decision must be 'APPROVE' or 'REJECT'.")

        new_status = "APPROVED" if decision_upper == "APPROVE" else "REJECTED"
        remediation.status = new_status
        remediation.reviewed_by_user_id = user_id
        remediation.reviewed_at = datetime.now(timezone.utc)
        remediation.review_comment = comment
        remediation.updated_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(remediation)

        action_name = "remediation_approved" if new_status == "APPROVED" else "remediation_rejected"
        await self.audit.log(
            user_id=user_id,
            action=action_name,
            resource_type="remediation",
            resource_id=str(remediation.id),
            metadata={"finding_id": str(remediation.finding_id), "comment": comment},
        )
        await self.db.commit()

        return remediation

    async def apply_remediation(
        self,
        *,
        remediation_id: uuid.UUID,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Remediation:
        """Mark remediation as applied to validation sandbox."""
        remediation = await self.db.get(Remediation, remediation_id)
        if not remediation or remediation.organization_id != organization_id:
            raise NotFoundError(f"Remediation '{remediation_id}' not found.")

        if remediation.status == "REJECTED":
            raise ValidationError("Cannot apply a rejected remediation.")

        # Ensure patch is valid
        PatchService.validate_patch_security(remediation.diff_content)

        remediation.status = "APPLIED"
        remediation.updated_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(remediation)

        await self.audit.log(
            user_id=user_id,
            action="remediation_applied",
            resource_type="remediation",
            resource_id=str(remediation.id),
            metadata={"finding_id": str(remediation.finding_id)},
        )
        await self.db.commit()

        return remediation

    async def validate_remediation(
        self,
        *,
        remediation_id: uuid.UUID,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        run_tests: bool = True,
        validation_policy: str = "v1.0.0",
    ) -> RemediationValidation:
        """Trigger multi-stage isolated validation."""
        val_service = ValidationService(self.db, self.storage)
        validation = await val_service.create_validation(
            remediation_id=remediation_id,
            actor_id=user_id,
        )
        # Execute pipeline
        completed = await val_service.execute_validation(
            validation.id,
            actor_id=user_id,
        )

        # Emit notification only for successful validation
        if user_id and completed.status == "passed":
            try:
                from backend.app.services.notification_service import NotificationService
                rem = await self.db.get(Remediation, remediation_id)
                if rem:
                    f = await self.db.get(Finding, rem.finding_id)
                    if f:
                        notif = NotificationService(self.db)
                        await notif.notify_fix_validated(
                            finding_id=f.id,
                            finding_public_id=f.public_id,
                            user_id=user_id,
                            organization_id=organization_id,
                            validation_status=completed.status,
                        )
                        await self.db.commit()
            except Exception as val_notif_err:
                logger.warning("Failed to emit fix_validated notification: {err}", err=val_notif_err)

        return completed

    async def get_verification_status(
        self,
        finding_id: uuid.UUID,
        organization_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Query authoritative finding verification status and evidence chain."""
        finding = await self.db.get(Finding, finding_id)
        if not finding or finding.organization_id != organization_id:
            raise NotFoundError(f"Finding '{finding_id}' not found.")

        # Latest remediation
        rem_stmt = (
            select(Remediation)
            .where(Remediation.finding_id == finding_id)
            .order_by(desc(Remediation.created_at))
            .limit(1)
        )
        rem_res = await self.db.execute(rem_stmt)
        latest_rem = rem_res.scalar_one_or_none()

        # Latest validation
        val_stmt = (
            select(RemediationValidation)
            .where(RemediationValidation.finding_id == finding_id)
            .order_by(desc(RemediationValidation.created_at))
            .limit(1)
        )
        val_res = await self.db.execute(val_stmt)
        latest_val = val_res.scalar_one_or_none()

        is_verified = finding.status == "VERIFIED"

        return {
            "finding_id": finding.id,
            "finding_status": finding.status,
            "is_verified": is_verified,
            "active_remediation_id": latest_rem.id if latest_rem else None,
            "active_remediation_status": latest_rem.status if latest_rem else None,
            "latest_validation_id": latest_val.id if latest_val else None,
            "latest_validation_status": latest_val.status if latest_val else None,
            "verification_scan_id": latest_val.verification_scan_id if latest_val else None,
            "final_verification_result": latest_val.final_verification_result if latest_val else None,
            "verified_at": finding.fixed_at if is_verified else None,
            "verification_details": {
                "patch_apply": latest_val.patch_apply_result.get("status") if latest_val else None,
                "syntax": latest_val.syntax_result.get("status") if latest_val else None,
                "build": latest_val.build_result.get("status") if latest_val else None,
                "tests": latest_val.test_result.get("status") if latest_val else None,
                "static_analysis": latest_val.static_analysis_result.get("status") if latest_val else None,
                "taint": latest_val.taint_result.get("status") if latest_val else None,
                "regression": latest_val.regression_result.get("status") if latest_val else None,
            } if latest_val else {},
        }
