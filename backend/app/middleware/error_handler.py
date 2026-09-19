# ============================================================
# Global Error Handler Middleware
# ============================================================
# Catches all exceptions and converts them to standardized
# response envelopes. Never returns raw stack traces.
# ============================================================

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.app.core.exceptions import AppError
from backend.app.core.logging import logger
from backend.app.core.response import error_response


def register_exception_handlers(app: FastAPI) -> None:
    """Register all global exception handlers on the FastAPI app."""

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        """Handle custom application errors."""
        logger.warning(
            "AppError [{code}]: {message} (status={status})",
            code=getattr(exc, "code", "APP_ERROR"),
            message=exc.message,
            status=exc.status_code,
        )
        req_id = getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID")
        headers = {}
        if getattr(exc, "retry_after", None) is not None:
            headers["Retry-After"] = str(exc.retry_after)

        return JSONResponse(
            status_code=exc.status_code,
            headers=headers,
            content=error_response(
                message=exc.message,
                errors=exc.details if exc.details else None,
                status_code=exc.status_code,
                code=getattr(exc, "code", "APP_ERROR"),
                request_id=req_id,
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        """Handle Pydantic / FastAPI validation errors."""
        errors = []
        for error in exc.errors():
            field = ".".join(str(loc) for loc in error.get("loc", []))
            errors.append({"field": field, "message": error.get("msg", "Invalid value")})

        first_err = errors[0] if errors else None
        msg = f"Validation failed: {first_err['message']} on '{first_err['field']}'" if first_err else "Validation failed"
        req_id = getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID")

        return JSONResponse(
            status_code=422,
            content=error_response(
                message=msg,
                errors=errors,
                status_code=422,
                code="VALIDATION_FAILED",
                request_id=req_id,
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """Handle standard HTTP exceptions (404, 405, etc.)."""
        req_id = getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID")
        code = f"HTTP_{exc.status_code}"
        if exc.status_code == 404:
            code = "NOT_FOUND"
        elif exc.status_code == 401:
            code = "AUTHENTICATION_REQUIRED"
        elif exc.status_code == 403:
            code = "PERMISSION_DENIED"

        return JSONResponse(
            status_code=exc.status_code,
            content=error_response(
                message=str(exc.detail),
                status_code=exc.status_code,
                code=code,
                request_id=req_id,
            ),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        """Catch-all for unhandled exceptions."""
        logger.exception("Unhandled exception: {exc}", exc=str(exc))
        req_id = getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID")
        return JSONResponse(
            status_code=500,
            content=error_response(
                message="An unexpected error occurred",
                status_code=500,
                code="INTERNAL_SERVER_ERROR",
                request_id=req_id,
            ),
        )
