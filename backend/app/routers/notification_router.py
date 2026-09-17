# ============================================================
# Notification Router
# ============================================================

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query

from backend.app.core.authorization import get_current_user
from backend.app.core.response import paginated_response, success_response
from backend.app.database.session import AsyncSession, get_db
from backend.app.models.user import User
from backend.app.schemas.notification import NotificationResponse, UnreadCountResponse
from backend.app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", summary="Get user notifications")
async def get_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    unread_only: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List notifications for the current user."""
    service = NotificationService(db)
    notifications, total = await service.get_user_notifications(
        current_user.id,
        page=page,
        page_size=page_size,
        unread_only=unread_only,
    )
    return paginated_response(
        items=[NotificationResponse.model_validate(n).model_dump(mode="json") for n in notifications],
        total=total,
        page=page,
        page_size=page_size,
        message="Notifications retrieved successfully",
    )


@router.get("/unread-count", summary="Get unread notification count")
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the number of unread notifications for the badge."""
    service = NotificationService(db)
    count = await service.get_unread_count(current_user.id)
    return success_response(
        data=UnreadCountResponse(count=count).model_dump(mode="json"),
        message="Unread count retrieved",
    )


@router.put("/{notification_id}/read", summary="Mark notification as read")
async def mark_read(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a single notification as read."""
    service = NotificationService(db)
    notification = await service.mark_as_read(notification_id, current_user.id)
    return success_response(
        data=NotificationResponse.model_validate(notification).model_dump(mode="json"),
        message="Notification marked as read",
    )


@router.put("/read-all", summary="Mark all notifications as read")
async def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark all unread notifications as read for the user."""
    service = NotificationService(db)
    count = await service.mark_all_as_read(current_user.id)
    return success_response(
        data={"updated_count": count},
        message=f"{count} notifications marked as read",
    )
