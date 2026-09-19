# ============================================================
# Notification Repository (Phase 7)
# ============================================================

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.notification import Notification
from backend.app.repositories.base import BaseRepository


class NotificationRepository(BaseRepository[Notification]):
    """Repository for Notification model operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, Notification)

    async def get_by_id_or_public_id(self, id_or_pid: str | uuid.UUID) -> Notification | None:
        """Find notification by internal UUID or public ID."""
        try:
            val_uuid = uuid.UUID(str(id_or_pid))
            stmt = select(Notification).where(
                (Notification.id == val_uuid) | (Notification.public_id == str(id_or_pid))
            )
        except ValueError:
            stmt = select(Notification).where(Notification.public_id == str(id_or_pid))

        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_event_key(self, user_id: uuid.UUID, event_key: str) -> Notification | None:
        """Find existing notification by user and event key for deduplication."""
        stmt = select(Notification).where(
            Notification.user_id == user_id,
            Notification.event_key == event_key,
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_user_notifications(
        self,
        user_id: uuid.UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        unread_only: bool = False,
        notification_type: str | None = None,
    ) -> tuple[Sequence[Notification], int]:
        """Get paginated notifications for a user."""
        filters = [Notification.user_id == user_id]
        if unread_only:
            filters.append(Notification.is_read.is_(False))
        if notification_type:
            filters.append(Notification.type == notification_type)

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
            .where(Notification.is_read.is_(False))
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
            .where(Notification.is_read.is_(False))
            .values(is_read=True, read_at=datetime.now(timezone.utc))
        )
        await self.db.flush()
        return result.rowcount
