# ============================================================
# Request ID Middleware
# ============================================================
# Assigns a unique X-Request-ID to every request.
# If the client provides one, it is reused.
# ============================================================

from __future__ import annotations

import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from backend.app.core.metrics import metrics


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach a unique request ID to each request/response and record operational metrics."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Use client-provided ID or generate a new one
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id

        start_time = time.time()
        metrics.increment("api_requests_total")

        try:
            response = await call_next(request)
        except Exception:
            metrics.increment("api_errors_total")
            raise
        else:
            if response.status_code >= 400:
                metrics.increment("api_errors_total")
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            duration_ms = (time.time() - start_time) * 1000.0
            metrics.observe("api_request_duration_ms", duration_ms)

