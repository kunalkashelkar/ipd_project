# ============================================================
# Centralized Scan Lifecycle Service (Phase 4)
# ============================================================

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from loguru import logger
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import ConflictError, NotFoundError, ValidationError
from backend.app.models.scan import Scan, ScanEvent, ScanStageRun
from backend.app.services.scan_lifecycle.state_machine import (
    InvalidStateTransitionError,
    ScanStage,
    ScanStateMachine,
    ScanStatus,
)


class ScanLifecycleService:
    """Orchestrates atomic scan transitions, stage history, events, and heartbeats."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_scan(self, scan_id: uuid.UUID) -> Scan:
        """Fetch scan or raise NotFoundError."""
        stmt = select(Scan).where(Scan.id == scan_id)
        res = await self.db.execute(stmt)
        scan = res.scalar_one_or_none()
        if not scan:
            raise NotFoundError(f"Scan {scan_id} not found")
        return scan

    async def transition_stage(
        self,
        scan_id: uuid.UUID,
        target_stage: ScanStage,
        *,
        worker_id: str | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        metadata: dict[str, Any] | None = None,
        force: bool = False,
    ) -> Scan:
        """Atomically transition a scan to target_stage and record stage run & event.

        Strictly enforces state machine rules unless force=True.
        """
        scan = await self.get_scan(scan_id)
        now = datetime.now(timezone.utc)

        current_stage = ScanStage(scan.current_stage or ScanStage.CREATED.value)

        # 1. State machine transition validation
        if not force:
            ScanStateMachine.validate_transition(current_stage, target_stage)

        # 2. Close out current stage run if it was active
        if current_stage != target_stage:
            stmt_prev = (
                select(ScanStageRun)
                .where(
                    ScanStageRun.scan_id == scan_id,
                    ScanStageRun.stage == current_stage.value,
                    ScanStageRun.attempt == scan.stage_attempt,
                    ScanStageRun.status == "running",
                )
                .order_by(ScanStageRun.created_at.desc())
            )
            res_prev = await self.db.execute(stmt_prev)
            prev_run = res_prev.scalars().first()
            if prev_run:
                prev_run.completed_at = now
                if prev_run.started_at:
                    s_at = prev_run.started_at
                    if s_at.tzinfo is None:
                        s_at = s_at.replace(tzinfo=timezone.utc)
                    prev_run.duration_seconds = max(0.0, (now - s_at).total_seconds())
                prev_run.status = "completed" if target_stage != ScanStage.FAILED else "failed"

        # 3. Update scan entity
        new_status = ScanStateMachine.stage_to_status(target_stage)
        new_progress = ScanStateMachine.calculate_progress(target_stage)

        scan.current_stage = target_stage.value
        scan.status = new_status.value
        scan.progress = new_progress

        if worker_id:
            scan.worker_id = worker_id
            scan.heartbeat_at = now

        if scan.started_at is None and target_stage not in {ScanStage.CREATED, ScanStage.QUEUED}:
            scan.started_at = now

        if ScanStateMachine.is_terminal(target_stage):
            scan.completed_at = now
            if target_stage == ScanStage.CANCELLED:
                scan.cancelled_at = now
                scan.failure_code = "CANCELLED"
                scan.failure_reason = "Scan was cancelled by user"
            elif target_stage == ScanStage.TIMED_OUT:
                scan.failure_code = error_code or "TIMED_OUT"
                scan.failure_reason = error_message or "Scan exceeded configured deadline"
            elif target_stage == ScanStage.FAILED:
                scan.failure_code = error_code or "ANALYSIS_FAILED"
                scan.failure_reason = error_message or "Internal analysis pipeline failure"
                scan.error_message = error_message

        # 4. Insert new ScanStageRun record for the target stage
        run_status = "completed" if target_stage == ScanStage.COMPLETED else ("failed" if target_stage == ScanStage.FAILED else "running")
        if target_stage == ScanStage.AI_ANALYSIS:
            # Explicitly mark reserved Phase 5 stage as skipped/not_configured
            run_status = "skipped"

        new_run = ScanStageRun(
            scan_id=scan_id,
            stage=target_stage.value,
            attempt=scan.stage_attempt,
            status=run_status,
            started_at=now,
            completed_at=now if run_status in {"completed", "failed", "skipped"} else None,
            duration_seconds=0.0 if run_status == "skipped" else None,
            worker_id=worker_id or scan.worker_id,
            error_code=error_code,
            error_message=error_message,
            stage_metadata=metadata or {},
        )
        self.db.add(new_run)

        # 5. Insert ScanEvent timeline record
        event = ScanEvent(
            scan_id=scan_id,
            event_type=f"scan.{target_stage.value}",
            stage=target_stage.value,
            payload={
                "attempt": scan.stage_attempt,
                "status": scan.status,
                "progress": scan.progress,
                "worker_id": worker_id or scan.worker_id,
                "error_code": error_code,
                **(metadata or {}),
            },
        )
        self.db.add(event)

        await self.db.commit()
        await self.db.refresh(scan)

        logger.info(
            "Scan {id} transitioned: {prev} -> {target} (status={status}, progress={p}%)",
            id=scan_id,
            prev=current_stage.value,
            target=target_stage.value,
            status=scan.status,
            p=scan.progress,
        )
        return scan

    async def record_heartbeat(self, scan_id: uuid.UUID, worker_id: str) -> None:
        """Update heartbeat timestamp to prove worker liveness."""
        now = datetime.now(timezone.utc)
        stmt = (
            update(Scan)
            .where(Scan.id == scan_id)
            .values(heartbeat_at=now, worker_id=worker_id)
        )
        await self.db.execute(stmt)
        await self.db.commit()

    async def cancel_scan(self, scan_id: uuid.UUID, user_id: uuid.UUID | None = None) -> Scan:
        """Cancel an active scan if permitted by state machine."""
        scan = await self.get_scan(scan_id)
        if not ScanStateMachine.is_cancellable(scan.current_stage or "created"):
            raise ConflictError(
                f"Cannot cancel scan in terminal or non-cancellable state '{scan.current_stage}'"
            )

        return await self.transition_stage(
            scan_id=scan_id,
            target_stage=ScanStage.CANCELLED,
            error_code="CANCELLED",
            error_message="Scan cancelled by user request",
            metadata={"cancelled_by": str(user_id) if user_id else None},
        )

    async def retry_scan(self, scan_id: uuid.UUID, max_retries: int = 3) -> Scan:
        """Attempt to retry a failed or timed out scan within bounded retries."""
        scan = await self.get_scan(scan_id)
        if scan.status not in {"failed", "timed_out"}:
            raise ConflictError(f"Cannot retry scan with status '{scan.status}'. Only failed or timed_out scans can be retried.")

        if scan.retry_count >= max_retries:
            raise ValidationError(
                f"Maximum retry limit ({max_retries}) exceeded for scan {scan_id}"
            )

        # Transition to RETRYING, increment attempts, then QUEUED
        scan.retry_count += 1
        scan.stage_attempt += 1
        await self.db.commit()

        await self.transition_stage(
            scan_id=scan_id,
            target_stage=ScanStage.RETRYING,
            metadata={"retry_count": scan.retry_count, "attempt": scan.stage_attempt},
        )

        return await self.transition_stage(
            scan_id=scan_id,
            target_stage=ScanStage.QUEUED,
            metadata={"requeued_attempt": scan.stage_attempt},
        )

    async def cleanup_stale_scans(self, max_stale_seconds: int = 1800) -> list[uuid.UUID]:
        """Detect and fail scans that have ceased heartbeating or timed out due to worker crash.

        Scans in active stages whose heartbeat_at (or started_at/created_at) is older than
        max_stale_seconds are transitioned to TIMED_OUT with code WORKER_UNRESPONSIVE.
        """
        now = datetime.now(timezone.utc)
        stmt = (
            select(Scan)
            .where(
                Scan.status.in_(["running", "queued"]),
            )
        )
        res = await self.db.execute(stmt)
        active_scans = res.scalars().all()
        recovered: list[uuid.UUID] = []
        for scan in active_scans:
            last_activity = scan.heartbeat_at or scan.started_at or scan.created_at
            if last_activity:
                if last_activity.tzinfo is None:
                    last_activity = last_activity.replace(tzinfo=timezone.utc)
                age = (now - last_activity).total_seconds()
                if age > max_stale_seconds:
                    logger.warning(
                        "Cleaning up stale scan {id} (last active {age:.1f}s ago)",
                        id=scan.id,
                        age=age,
                    )
                    await self.transition_stage(
                        scan.id,
                        target_stage=ScanStage.TIMED_OUT,
                        error_code="WORKER_UNRESPONSIVE",
                        error_message=f"Scan heartbeat expired after {int(age)}s without worker activity.",
                        force=True,
                    )
                    recovered.append(scan.id)
        return recovered

