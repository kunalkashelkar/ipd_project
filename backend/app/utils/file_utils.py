# ============================================================
# File Utilities
# ============================================================

from __future__ import annotations

from pathlib import Path

from backend.app.core.exceptions import ValidationError


def validate_file_extension(filename: str, allowed_extensions: list[str]) -> None:
    """Check if the file extension is allowed."""
    ext = Path(filename).suffix.lower()
    if ext not in allowed_extensions:
        raise ValidationError(
            f"File extension {ext} not allowed. Allowed: {', '.join(allowed_extensions)}"
        )


def validate_file_size(size_bytes: int, max_size_bytes: int) -> None:
    """Check if the file size is within limits."""
    if size_bytes > max_size_bytes:
        max_mb = max_size_bytes / (1024 * 1024)
        raise ValidationError(f"File too large. Maximum size is {max_mb:.0f}MB")
