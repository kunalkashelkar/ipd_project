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
            "AppError: {message} (status={status})",
            message=exc.message,
            status=exc.status_code,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response(
                message=exc.message,
                errors=exc.details if exc.details else None,
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        """Handle Pydantic / FastAPI validation errors."""
        errors = []
        for error in exc.errors():
            field = ".".join(str(loc) for loc in error.get("loc", []))
            errors.append({"field": field, "message": error.get("msg", "Invalid value")})

        return JSONResponse(
            status_code=422,
            content=error_response(
                message="Validation failed",
                errors=errors,
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """Handle standard HTTP exceptions (404, 405, etc.)."""
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response(
                message=str(exc.detail),
            ),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        """Catch-all for unhandled exceptions."""
        logger.exception("Unhandled exception: {exc}", exc=str(exc))
        return JSONResponse(
            status_code=500,
            content=error_response(
                message="An unexpected error occurred",
            ),
        )
