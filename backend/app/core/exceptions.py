# ============================================================
# Custom Exception Hierarchy
# ============================================================
# All business exceptions extend AppError.
# The global exception handler converts these to standard
# response envelopes — no raw stack traces to clients.
# ============================================================

from __future__ import annotations


class AppError(Exception):
    """Base application error."""

    status_code: int = 500
    message: str = "An unexpected error occurred"

    def __init__(self, message: str | None = None, *, details: list[dict] | None = None):
        self.message = message or self.__class__.message
        self.details = details or []
        super().__init__(self.message)


# ── Authentication / Authorization ─────────────────────────


class AuthenticationError(AppError):
    """Invalid credentials or expired token."""

    status_code = 401
    message = "Authentication failed"


class AuthorizationError(AppError):
    """User lacks required permissions."""

    status_code = 403
    message = "Insufficient permissions"


# ── Validation ─────────────────────────────────────────────


class ValidationError(AppError):
    """Request data failed validation."""

    status_code = 422
    message = "Validation failed"


# ── Resource Errors ────────────────────────────────────────


class NotFoundError(AppError):
    """Requested resource does not exist."""

    status_code = 404
    message = "Resource not found"


class ConflictError(AppError):
    """Resource already exists or state conflict."""

    status_code = 409
    message = "Resource conflict"


# ── Domain Errors ──────────────────────────────────────────


class StorageError(AppError):
    """File storage operation failed."""

    status_code = 500
    message = "Storage operation failed"


class PreprocessingError(AppError):
    """File preprocessing failed."""

    status_code = 500
    message = "Preprocessing failed"


class ScanError(AppError):
    """Scan operation failed."""

    status_code = 500
    message = "Scan operation failed"


class AIError(AppError):
    """AI inference failed."""

    status_code = 500
    message = "AI prediction failed"


class ReportError(AppError):
    """Report generation failed."""

    status_code = 500
    message = "Report generation failed"
