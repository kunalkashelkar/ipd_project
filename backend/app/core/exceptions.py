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
    code: str = "INTERNAL_ERROR"
    message: str = "An unexpected error occurred"

    def __init__(
        self,
        message: str | None = None,
        *,
        details: list[dict] | None = None,
        code: str | None = None,
    ):
        self.message = message or self.__class__.message
        self.code = code or self.__class__.code
        self.details = details or []
        super().__init__(self.message)


# ── Authentication / Authorization ─────────────────────────


class AuthenticationError(AppError):
    """Invalid credentials or expired token."""

    status_code = 401
    code = "AUTHENTICATION_REQUIRED"
    message = "Authentication failed"


class AuthorizationError(AppError):
    """User lacks required permissions."""

    status_code = 403
    code = "PERMISSION_DENIED"
    message = "Insufficient permissions"


# ── Validation / Bad Request ───────────────────────────────


class BadRequestError(AppError):
    """Client request is invalid or unsupported."""

    status_code = 400
    code = "BAD_REQUEST"
    message = "Bad request"


class ValidationError(AppError):
    """Request data failed validation."""

    status_code = 422
    code = "VALIDATION_FAILED"
    message = "Validation failed"


# ── Resource Errors ────────────────────────────────────────


class NotFoundError(AppError):
    """Requested resource does not exist."""

    status_code = 404
    code = "NOT_FOUND"
    message = "Resource not found"


class ConflictError(AppError):
    """Resource already exists or state conflict."""

    status_code = 409
    code = "CONFLICT"
    message = "Resource conflict"


# ── Domain Errors ──────────────────────────────────────────


class StorageError(AppError):
    """File storage operation failed."""

    status_code = 500
    code = "STORAGE_ERROR"
    message = "Storage operation failed"


class PreprocessingError(AppError):
    """File preprocessing failed."""

    status_code = 500
    code = "PREPROCESSING_ERROR"
    message = "Preprocessing failed"


class ScanError(AppError):
    """Scan operation failed."""

    status_code = 500
    code = "SCAN_ERROR"
    message = "Scan operation failed"


class AIError(AppError):
    """AI inference failed."""

    status_code = 500
    code = "AI_ERROR"
    message = "AI prediction failed"


class ReportError(AppError):
    """Report generation failed."""

    status_code = 500
    code = "REPORT_ERROR"
    message = "Report generation failed"


class RateLimitExceededError(AppError):
    """Rate limit exceeded."""

    status_code = 429
    code = "RATE_LIMIT_EXCEEDED"
    message = "Too many requests. Please try again later."

    def __init__(
        self,
        message: str | None = None,
        *,
        retry_after: int = 60,
        details: list[dict] | None = None,
        code: str | None = None,
    ):
        super().__init__(message, details=details, code=code or "RATE_LIMIT_EXCEEDED")
        self.retry_after = retry_after


class ModelIntegrityError(AppError):
    """Model artifact failed integrity or checksum validation."""

    status_code = 500
    code = "MODEL_INTEGRITY_FAILURE"
    message = "Model artifact failed integrity verification: Checksum mismatch or corruption detected"


