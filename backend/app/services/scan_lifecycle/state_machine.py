# ============================================================
# Centralized Scan State Machine (Phase 4)
# ============================================================

from __future__ import annotations

from enum import Enum
from typing import Set


class ScanStage(str, Enum):
    """Execution stages of a vulnerability analysis scan."""

    CREATED = "created"
    QUEUED = "queued"
    PREPARING = "preparing"
    CHECKOUT = "checkout"
    PREPROCESSING = "preprocessing"
    STATIC_ANALYSIS = "static_analysis"
    GRAPH_PROCESSING = "graph_processing"
    AI_ANALYSIS = "ai_analysis"
    POST_PROCESSING = "post_processing"
    COMPLETED = "completed"

    # Terminal error states
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"

    # Retry state
    RETRYING = "retrying"


class ScanStatus(str, Enum):
    """Overall high-level lifecycle status of a scan."""

    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"
    RETRYING = "retrying"


class InvalidStateTransitionError(ValueError):
    """Raised when an illegal scan lifecycle transition is attempted."""


class ScanStateMachine:
    """Central authority on valid scan stage and status transitions."""

    # Active processing stages in chronological execution order
    ACTIVE_STAGE_SEQUENCE = [
        ScanStage.CREATED,
        ScanStage.QUEUED,
        ScanStage.PREPARING,
        ScanStage.CHECKOUT,
        ScanStage.PREPROCESSING,
        ScanStage.STATIC_ANALYSIS,
        ScanStage.GRAPH_PROCESSING,
        ScanStage.AI_ANALYSIS,
        ScanStage.POST_PROCESSING,
        ScanStage.COMPLETED,
    ]

    TERMINAL_STAGES: Set[ScanStage] = {
        ScanStage.COMPLETED,
        ScanStage.FAILED,
        ScanStage.CANCELLED,
        ScanStage.TIMED_OUT,
    }

    CANCELLABLE_STAGES: Set[ScanStage] = {
        ScanStage.CREATED,
        ScanStage.QUEUED,
        ScanStage.PREPARING,
        ScanStage.CHECKOUT,
        ScanStage.PREPROCESSING,
        ScanStage.STATIC_ANALYSIS,
        ScanStage.GRAPH_PROCESSING,
        ScanStage.AI_ANALYSIS,
        ScanStage.POST_PROCESSING,
        ScanStage.RETRYING,
    }

    # Explicit mapping of permitted forward and terminal transitions
    ALLOWED_TRANSITIONS: dict[ScanStage, Set[ScanStage]] = {
        ScanStage.CREATED: {ScanStage.QUEUED, ScanStage.CANCELLED, ScanStage.FAILED},
        ScanStage.QUEUED: {ScanStage.PREPARING, ScanStage.CANCELLED, ScanStage.TIMED_OUT, ScanStage.FAILED},
        ScanStage.PREPARING: {ScanStage.CHECKOUT, ScanStage.CANCELLED, ScanStage.TIMED_OUT, ScanStage.FAILED},
        ScanStage.CHECKOUT: {ScanStage.PREPROCESSING, ScanStage.CANCELLED, ScanStage.TIMED_OUT, ScanStage.FAILED},
        ScanStage.PREPROCESSING: {ScanStage.STATIC_ANALYSIS, ScanStage.CANCELLED, ScanStage.TIMED_OUT, ScanStage.FAILED},
        ScanStage.STATIC_ANALYSIS: {ScanStage.GRAPH_PROCESSING, ScanStage.CANCELLED, ScanStage.TIMED_OUT, ScanStage.FAILED},
        ScanStage.GRAPH_PROCESSING: {ScanStage.AI_ANALYSIS, ScanStage.CANCELLED, ScanStage.TIMED_OUT, ScanStage.FAILED},
        ScanStage.AI_ANALYSIS: {ScanStage.POST_PROCESSING, ScanStage.CANCELLED, ScanStage.TIMED_OUT, ScanStage.FAILED},
        ScanStage.POST_PROCESSING: {ScanStage.COMPLETED, ScanStage.CANCELLED, ScanStage.TIMED_OUT, ScanStage.FAILED},
        ScanStage.RETRYING: {ScanStage.QUEUED, ScanStage.PREPARING, ScanStage.FAILED, ScanStage.CANCELLED},
        ScanStage.FAILED: {ScanStage.RETRYING},
        ScanStage.TIMED_OUT: {ScanStage.RETRYING},
        ScanStage.CANCELLED: set(),
        ScanStage.COMPLETED: set(),
    }

    @classmethod
    def can_transition(cls, current_stage: str | ScanStage, target_stage: str | ScanStage) -> bool:
        """Check if transition from current_stage to target_stage is allowed."""
        try:
            cur = ScanStage(current_stage)
            target = ScanStage(target_stage)
        except ValueError:
            return False
        return target in cls.ALLOWED_TRANSITIONS.get(cur, set())

    @classmethod
    def validate_transition(cls, current_stage: str | ScanStage, target_stage: str | ScanStage) -> None:
        """Validate transition, raising InvalidStateTransitionError if illegal."""
        cur = ScanStage(current_stage) if isinstance(current_stage, str) else current_stage
        target = ScanStage(target_stage) if isinstance(target_stage, str) else target_stage
        if not cls.can_transition(cur, target):
            raise InvalidStateTransitionError(
                f"Illegal scan lifecycle transition: cannot transition from '{cur.value}' to '{target.value}'"
            )

    @classmethod
    def is_terminal(cls, stage: str | ScanStage) -> bool:
        """Return True if stage is terminal."""
        try:
            s = ScanStage(stage)
            return s in cls.TERMINAL_STAGES
        except ValueError:
            return False

    @classmethod
    def is_cancellable(cls, stage: str | ScanStage) -> bool:
        """Return True if scan in this stage can be cancelled."""
        try:
            s = ScanStage(stage)
            return s in cls.CANCELLABLE_STAGES
        except ValueError:
            return False

    @classmethod
    def stage_to_status(cls, stage: ScanStage) -> ScanStatus:
        """Map granular stage to high-level status."""
        if stage == ScanStage.CREATED:
            return ScanStatus.PENDING
        if stage == ScanStage.QUEUED:
            return ScanStatus.QUEUED
        if stage in cls.TERMINAL_STAGES:
            return ScanStatus(stage.value)
        if stage == ScanStage.RETRYING:
            return ScanStatus.RETRYING
        return ScanStatus.RUNNING

    @classmethod
    def calculate_progress(cls, stage: ScanStage) -> float:
        """Return deterministic progress percentage based on stage."""
        progress_map = {
            ScanStage.CREATED: 0.0,
            ScanStage.QUEUED: 5.0,
            ScanStage.PREPARING: 10.0,
            ScanStage.CHECKOUT: 20.0,
            ScanStage.PREPROCESSING: 35.0,
            ScanStage.STATIC_ANALYSIS: 55.0,
            ScanStage.GRAPH_PROCESSING: 75.0,
            ScanStage.AI_ANALYSIS: 85.0,  # Explicitly passed/reserved
            ScanStage.POST_PROCESSING: 95.0,
            ScanStage.COMPLETED: 100.0,
            ScanStage.FAILED: 100.0,
            ScanStage.CANCELLED: 100.0,
            ScanStage.TIMED_OUT: 100.0,
            ScanStage.RETRYING: 0.0,
        }
        return progress_map.get(stage, 0.0)
