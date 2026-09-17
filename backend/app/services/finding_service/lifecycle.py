# ============================================================
# Finding Lifecycle Transition Policy (Phase 5)
# ============================================================
# Enforces valid status transitions for findings:
#   OPEN -> CONFIRMED, IN_PROGRESS, FALSE_POSITIVE, RISK_ACCEPTED, SUPPRESSED
#   CONFIRMED -> IN_PROGRESS, FALSE_POSITIVE, RISK_ACCEPTED, SUPPRESSED
#   IN_PROGRESS -> FIX_PROPOSED, CONFIRMED, FALSE_POSITIVE, RISK_ACCEPTED, SUPPRESSED
#   FIX_PROPOSED -> UNDER_REVIEW, IN_PROGRESS
#   UNDER_REVIEW -> FIXED, IN_PROGRESS
#   FIXED -> VERIFIED, REOPENED
#   FALSE_POSITIVE, RISK_ACCEPTED, SUPPRESSED -> REOPENED, OPEN
#   REOPENED -> CONFIRMED, IN_PROGRESS
# ============================================================

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import ValidationError
from backend.app.models.finding import Finding, FindingStatusHistory
from backend.app.services.audit_service import AuditService

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "OPEN": {"CONFIRMED", "IN_PROGRESS", "FALSE_POSITIVE", "RISK_ACCEPTED", "SUPPRESSED"},
    "CONFIRMED": {"IN_PROGRESS", "FALSE_POSITIVE", "RISK_ACCEPTED", "SUPPRESSED"},
    "IN_PROGRESS": {"FIX_PROPOSED", "CONFIRMED", "FALSE_POSITIVE", "RISK_ACCEPTED", "SUPPRESSED"},
    "FIX_PROPOSED": {"UNDER_REVIEW", "IN_PROGRESS"},
    "UNDER_REVIEW": {"FIXED", "IN_PROGRESS"},
    "FIXED": {"VERIFIED", "REOPENED"},
    "VERIFIED": {"REOPENED"},
    "FALSE_POSITIVE": {"OPEN", "REOPENED"},
    "RISK_ACCEPTED": {"OPEN", "REOPENED"},
    "SUPPRESSED": {"OPEN", "REOPENED"},
    "REOPENED": {"CONFIRMED", "IN_PROGRESS", "FALSE_POSITIVE", "RISK_ACCEPTED", "SUPPRESSED"},
}


class FindingLifecycleService:
    """Central transition controller for finding lifecycle states."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.audit = AuditService(db)

    def validate_transition(self, current_status: str, target_status: str) -> None:
        """Validate if a transition from current_status to target_status is allowed."""
        curr = current_status.upper().strip()
        target = target_status.upper().strip()

        allowed = ALLOWED_TRANSITIONS.get(curr, set())
        if target not in allowed:
            raise ValidationError(
                f"Invalid finding status transition from '{curr}' to '{target}'. "
                f"Allowed target states: {sorted(list(allowed))}"
            )

    async def transition_status(
        self,
        finding: Finding,
        new_status: str,
        *,
        actor_id: uuid.UUID | None = None,
        reason: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> FindingStatusHistory:
        """Execute a validated status transition and record historical audit log."""
        target_status = new_status.upper().strip()
        previous_status = finding.status

        # If unchanged, do nothing
        if target_status == previous_status:
            return FindingStatusHistory(
                id=uuid.uuid4(),
                finding_id=finding.id,
                previous_status=previous_status,
                new_status=target_status,
                actor_id=actor_id,
                reason="Status unchanged",
                change_metadata=metadata,
                created_at=datetime.now(timezone.utc),
            )

        self.validate_transition(previous_status, target_status)

        # Update finding attributes
        finding.status = target_status
        finding.updated_at = datetime.now(timezone.utc)
        if target_status in ("FIXED", "VERIFIED"):
            finding.fixed_at = datetime.now(timezone.utc)
        elif target_status in ("OPEN", "REOPENED", "IN_PROGRESS"):
            finding.fixed_at = None

        # Record status history row
        history = FindingStatusHistory(
            id=uuid.uuid4(),
            finding_id=finding.id,
            previous_status=previous_status,
            new_status=target_status,
            actor_id=actor_id,
            reason=reason,
            change_metadata=metadata,
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(history)
        await self.db.flush()

        # Audit log event
        action_name = "finding_status_changed"
        if target_status == "SUPPRESSED":
            action_name = "finding_suppressed"
        elif target_status == "RISK_ACCEPTED":
            action_name = "risk_accepted"
        elif target_status in ("OPEN", "REOPENED") and previous_status in ("SUPPRESSED", "FALSE_POSITIVE"):
            action_name = "finding_unsuppressed"
        elif target_status in ("OPEN", "REOPENED") and previous_status == "RISK_ACCEPTED":
            action_name = "risk_acceptance_removed"

        await self.audit.log(
            user_id=actor_id,
            action=action_name,
            resource_type="finding",
            resource_id=str(finding.id),
            metadata={
                "previous_status": previous_status,
                "new_status": target_status,
                "reason": reason,
                **(metadata or {}),
            },
        )

        return history
