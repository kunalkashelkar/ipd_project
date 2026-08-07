# ============================================================
# Notification Service
# ============================================================

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.repositories.notification_repository import NotificationRepository


class NotificationService:
    """Business logic for notifications."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = NotificationRepository(db)

    async def get_user_notifications(
        self,
        user_id: uuid.UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        unread_only: bool = False,
    ):
        """Get paginated notifications for a user."""
        return await self.repo.get_user_notifications(
            user_id, page=page, page_size=page_size, unread_only=unread_only
        )

    async def get_unread_count(self, user_id: uuid.UUID) -> int:
        """Get count of unread notifications."""
        return await self.repo.get_unread_count(user_id)

    async def mark_as_read(self, notification_id: uuid.UUID, user_id: uuid.UUID):
        """Mark a single notification as read."""
        notification = await self.repo.get_by_id(notification_id)
        if not notification or notification.user_id != user_id:
            from backend.app.core.exceptions import NotFoundError
            raise NotFoundError("Notification not found")

        return await self.repo.mark_read(notification_id)

    async def mark_all_as_read(self, user_id: uuid.UUID) -> int:
        """Mark all notifications as read."""
        return await self.repo.mark_all_read(user_id)
