# ============================================================
# Notification Model (Phase 7)
# ============================================================

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.identifiers import PREFIX_NOTIFICATION, generate_public_id
from backend.app.database.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.organization import Organization
    from backend.app.models.user import User


class Notification(Base, UUIDPrimaryKeyMixin):
    """In-app persistent notification for a user."""

    __tablename__ = "notifications"

    public_id: Mapped[str] = mapped_column(
        String(32),
        unique=True,
        index=True,
        nullable=False,
        default=lambda: generate_public_id(PREFIX_NOTIFICATION),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True
    )
    type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # scan_completed, scan_failed, critical_finding, fix_ready, fix_validated, finding_reopened, repository_disconnected, user_mentioned, report_ready, system
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="info")  # info, warning, critical, success
    entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)  # scan, report, project, finding, repository
    entity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    link_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    event_key: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="notifications")
    organization: Mapped["Organization | None"] = relationship("Organization")
