# ============================================================
# Notification Service (Phase 7 — Authoritative Domain Events)
# ============================================================

from __future__ import annotations

import uuid
from typing import Any, Sequence

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import NotFoundError
from backend.app.models.notification import Notification
from backend.app.models.organization import OrganizationMember
from backend.app.repositories.notification_repository import NotificationRepository


class NotificationService:
    """Authoritative notification dispatch, deduplication, and querying."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = NotificationRepository(db)

    async def create_notification(
        self,
        *,
        user_id: uuid.UUID,
        type: str,
        title: str,
        body: str | None = None,
        severity: str = "info",
        organization_id: uuid.UUID | None = None,
        entity_type: str | None = None,
        entity_id: uuid.UUID | None = None,
        link_url: str | None = None,
        event_key: str | None = None,
    ) -> Notification:
        """Create a persistent in-app notification with idempotency protection."""
        if event_key:
            existing = await self.repo.get_by_event_key(user_id, event_key)
            if existing:
                logger.debug(
                    "Notification deduplicated for user {uid} with event_key {key}",
                    uid=user_id,
                    key=event_key,
                )
                return existing

        notification = await self.repo.create(
            user_id=user_id,
            organization_id=organization_id,
            type=type,
            title=title,
            body=body,
            severity=severity,
            entity_type=entity_type,
            entity_id=entity_id,
            link_url=link_url,
            event_key=event_key,
            is_read=False,
        )
        return notification

    async def notify_organization_members(
        self,
        organization_id: uuid.UUID,
        *,
        type: str,
        title: str,
        body: str | None = None,
        severity: str = "info",
        entity_type: str | None = None,
        entity_id: uuid.UUID | None = None,
        link_url: str | None = None,
        event_key_prefix: str | None = None,
    ) -> list[Notification]:
        """Broadcast a notification to all active members of an organization."""
        member_stmt = select(OrganizationMember).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.status == "active",
        )
        res = await self.db.execute(member_stmt)
        members = res.scalars().all()

        notifications = []
        for m in members:
            key = f"{event_key_prefix}:{m.user_id}" if event_key_prefix else None
            notif = await self.create_notification(
                user_id=m.user_id,
                organization_id=organization_id,
                type=type,
                title=title,
                body=body,
                severity=severity,
                entity_type=entity_type,
                entity_id=entity_id,
                link_url=link_url,
                event_key=key,
            )
            notifications.append(notif)

        return notifications

    # ── Canonical Domain Event Triggers ──────────────────────

    async def notify_scan_completed(
        self,
        scan_id: uuid.UUID,
        public_scan_id: str,
        project_id: uuid.UUID,
        project_name: str,
        organization_id: uuid.UUID,
    ) -> None:
        """Trigger notification on scan completion."""
        await self.notify_organization_members(
            organization_id,
            type="scan_completed",
            title=f"Scan Completed: {project_name}",
            body=f"Analysis scan {public_scan_id} has completed successfully.",
            severity="info",
            entity_type="scan",
            entity_id=scan_id,
            link_url=f"/projects/{project_id}/results?scan_id={public_scan_id}",
            event_key_prefix=f"scan_completed:{scan_id}",
        )

    async def notify_critical_finding(
        self,
        finding_id: uuid.UUID,
        finding_public_id: str,
        title: str,
        project_id: uuid.UUID,
        organization_id: uuid.UUID,
    ) -> None:
        """Trigger alert when a new Critical severity finding is detected."""
        await self.notify_organization_members(
            organization_id,
            type="critical_finding",
            title="Critical Finding Detected",
            body=f"Critical vulnerability identified: {title} ({finding_public_id})",
            severity="critical",
            entity_type="finding",
            entity_id=finding_id,
            link_url=f"/findings/{finding_public_id}",
            event_key_prefix=f"critical_finding:{finding_id}",
        )

    async def notify_fix_ready(
        self,
        finding_id: uuid.UUID,
        finding_public_id: str,
        user_id: uuid.UUID,
        organization_id: uuid.UUID,
        remediation_id: uuid.UUID,
    ) -> None:
        """Trigger notification when an AI remediation proposal is ready."""
        await self.create_notification(
            user_id=user_id,
            organization_id=organization_id,
            type="fix_ready",
            title="Remediation Proposed",
            body=f"An automated patch proposal is ready for review on finding {finding_public_id}.",
            severity="info",
            entity_type="remediation",
            entity_id=remediation_id,
            link_url=f"/findings/{finding_public_id}",
            event_key=f"fix_ready:{remediation_id}:{user_id}",
        )

    async def notify_fix_validated(
        self,
        finding_id: uuid.UUID,
        finding_public_id: str,
        user_id: uuid.UUID,
        organization_id: uuid.UUID,
        validation_status: str,
    ) -> None:
        """Trigger notification when remediation validation finishes."""
        sev = "success" if validation_status == "passed" else "warning"
        await self.create_notification(
            user_id=user_id,
            organization_id=organization_id,
            type="fix_validated",
            title=f"Fix Validation {validation_status.capitalize()}",
            body=f"Remediation patch validation {validation_status} for finding {finding_public_id}.",
            severity=sev,
            entity_type="finding",
            entity_id=finding_id,
            link_url=f"/findings/{finding_public_id}",
            event_key=f"fix_validated:{finding_id}:{validation_status}:{user_id}",
        )

    async def notify_finding_reopened(
        self,
        finding_id: uuid.UUID,
        finding_public_id: str,
        title: str,
        organization_id: uuid.UUID,
    ) -> None:
        """Trigger notification when a resolved/suppressed finding re-occurs."""
        await self.notify_organization_members(
            organization_id,
            type="finding_reopened",
            title="Finding Reopened",
            body=f"Previously resolved finding has re-occurred: {title} ({finding_public_id})",
            severity="warning",
            entity_type="finding",
            entity_id=finding_id,
            link_url=f"/findings/{finding_public_id}",
            event_key_prefix=f"finding_reopened:{finding_id}",
        )

    async def notify_repository_disconnected(
        self,
        repo_id: uuid.UUID,
        repo_url: str | None,
        organization_id: uuid.UUID,
    ) -> None:
        """Trigger notification when a repository connection is disconnected."""
        await self.notify_organization_members(
            organization_id,
            type="repository_disconnected",
            title="Repository Disconnected",
            body=f"Repository {repo_url or 'linked VCS'} was disconnected.",
            severity="warning",
            entity_type="repository",
            entity_id=repo_id,
            link_url="/integrations",
            event_key_prefix=f"repo_disconnected:{repo_id}",
        )

    async def notify_user_mentioned(
        self,
        comment_id: uuid.UUID,
        finding_id: uuid.UUID,
        finding_public_id: str,
        mentioned_user_id: uuid.UUID,
        author_name: str,
        organization_id: uuid.UUID,
    ) -> None:
        """Trigger notification when an organization member is mentioned in a finding comment."""
        await self.create_notification(
            user_id=mentioned_user_id,
            organization_id=organization_id,
            type="user_mentioned",
            title=f"Mentioned by {author_name}",
            body=f"{author_name} mentioned you in a comment on finding {finding_public_id}.",
            severity="info",
            entity_type="finding",
            entity_id=finding_id,
            link_url=f"/findings/{finding_public_id}",
            event_key=f"mention:{comment_id}:{mentioned_user_id}",
        )

    # ── Notification Management Methods ──────────────────────

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
        return await self.repo.get_user_notifications(
            user_id,
            page=page,
            page_size=page_size,
            unread_only=unread_only,
            notification_type=notification_type,
        )

    async def get_unread_count(self, user_id: uuid.UUID) -> int:
        """Get count of unread notifications."""
        return await self.repo.get_unread_count(user_id)

    async def mark_as_read(self, notification_id: uuid.UUID, user_id: uuid.UUID) -> Notification:
        """Mark a single notification as read."""
        notification = await self.repo.get_by_id_or_public_id(notification_id)
        if not notification or notification.user_id != user_id:
            raise NotFoundError("Notification not found")

        return await self.repo.mark_read(notification.id)

    async def mark_all_as_read(self, user_id: uuid.UUID) -> int:
        """Mark all notifications as read."""
        return await self.repo.mark_all_read(user_id)
