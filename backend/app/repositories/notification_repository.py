# ============================================================
# Notification Repository
# ============================================================

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.notification import Notification
from backend.app.repositories.base import BaseRepository


class NotificationRepository(BaseRepository[Notification]):
    """Repository for Notification model operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, Notification)

    async def get_user_notifications(
        self,
        user_id: uuid.UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        unread_only: bool = False,
    ) -> tuple[list[Notification], int]:
        """Get notifications for a user."""
        filters = [Notification.user_id == user_id]
        if unread_only:
            filters.append(Notification.is_read == False)  # noqa: E712

        return await self.get_all(
            page=page,
            page_size=page_size,
            filters=filters,
            order_by=Notification.created_at.desc(),
        )

    async def get_unread_count(self, user_id: uuid.UUID) -> int:
        """Get count of unread notifications."""
        result = await self.db.execute(
            select(func.count())
            .select_from(Notification)
            .where(Notification.user_id == user_id)
            .where(Notification.is_read == False)  # noqa: E712
        )
        return result.scalar() or 0

    async def mark_read(self, notification_id: uuid.UUID) -> Notification | None:
        """Mark a notification as read."""
        return await self.update(
            notification_id,
            is_read=True,
            read_at=datetime.now(timezone.utc),
        )

    async def mark_all_read(self, user_id: uuid.UUID) -> int:
        """Mark all notifications as read for a user."""
        result = await self.db.execute(
            update(Notification)
            .where(Notification.user_id == user_id)
            .where(Notification.is_read == False)  # noqa: E712
            .values(is_read=True, read_at=datetime.now(timezone.utc))
        )
        await self.db.flush()
        return result.rowcount
