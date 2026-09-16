# ============================================================
# Session and Verification Token Models
# ============================================================

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, UTCDateTime

if TYPE_CHECKING:
    from backend.app.models.user import User


class UserSession(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Server-tracked revocable session supporting JWT refresh and logout."""

    __tablename__ = "sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    last_used_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), server_default=func.now(), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="sessions")

    @property
    def is_active(self) -> bool:
        """Check if session is neither revoked nor expired."""
        now = datetime.now(timezone.utc)
        return self.revoked_at is None and self.expires_at > now


class VerificationToken(Base, UUIDPrimaryKeyMixin):
    """Cryptographically hashed one-time token for email verification and password resets."""

    __tablename__ = "verification_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_type: Mapped[str] = mapped_column(
        String(30), nullable=False, index=True
    )  # email_verification, password_reset
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), server_default=func.now(), nullable=False
    )


    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="verification_tokens")

    @property
    def is_valid(self) -> bool:
        """Check if token is unconsumed and unexpired."""
        now = datetime.now(datetime.now().astimezone().tzinfo)
        return self.used_at is None and self.expires_at > now
