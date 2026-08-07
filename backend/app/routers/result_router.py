# ============================================================
# Result Router — Vulnerability Findings
# ============================================================

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query

from backend.app.core.permissions import get_current_active_user
from backend.app.core.response import paginated_response, success_response
from backend.app.database.session import AsyncSession, get_db
from backend.app.schemas.result import FeedbackCreate, FeedbackResponse, ScanResultResponse
from backend.app.services.result_service import ResultService

router = APIRouter(prefix="/results", tags=["Results"])


@router.get("/scans/{scan_id}", summary="Get paginated scan results")
async def get_scan_results(
    scan_id: uuid.UUID,
    severity: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all vulnerability findings for a specific scan."""
    service = ResultService(db)
    results, total = await service.get_scan_results(
        scan_id=scan_id,
        user_id=current_user.id,
        role=current_user.role,
        page=page,
        page_size=page_size,
        severity=severity,
    )
    return paginated_response(
        items=[ScanResultResponse.model_validate(r).model_dump(mode="json") for r in results],
        total=total,
        page=page,
        page_size=page_size,
        message="Results retrieved successfully",
    )


@router.get("/scans/{scan_id}/summary", summary="Get scan results summary")
async def get_scan_summary(
    scan_id: uuid.UUID,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get aggregated vulnerability statistics for a scan."""
    service = ResultService(db)
    summary = await service.get_scan_summary(scan_id)
    return success_response(
        data=summary,
        message="Scan summary retrieved successfully",
    )


@router.post("/{result_id}/feedback", summary="Submit feedback on a result")
async def submit_feedback(
    result_id: uuid.UUID,
    body: FeedbackCreate,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit human feedback (correct/incorrect) on an AI prediction."""
    service = ResultService(db)
    feedback = await service.submit_feedback(
        result_id=result_id,
        user_id=current_user.id,
        is_correct=body.is_correct,
        comment=body.comment,
    )
    return success_response(
        data=FeedbackResponse.model_validate(feedback).model_dump(mode="json"),
        message="Feedback submitted successfully",
        status_code=201,
    )
