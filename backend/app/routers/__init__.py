# ============================================================
# Routers Package — register all endpoints
# ============================================================

from backend.app.routers.auth_router import router as auth_router
from backend.app.routers.health_router import router as health_router
from backend.app.routers.project_router import router as project_router
from backend.app.routers.upload_router import router as upload_router
from backend.app.routers.scan_router import router as scan_router
from backend.app.routers.result_router import router as result_router
from backend.app.routers.report_router import router as report_router
from backend.app.routers.websocket_router import router as websocket_router
from backend.app.routers.notification_router import router as notification_router
from backend.app.routers.analytics_router import router as analytics_router

__all__ = [
    "auth_router",
    "health_router",
    "project_router",
    "upload_router",
    "scan_router",
    "result_router",
    "report_router",
    "websocket_router",
    "notification_router",
    "analytics_router",
]
