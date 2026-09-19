# ============================================================
# Routers Package — register all endpoints
# ============================================================

from backend.app.routers.analytics_router import router as analytics_router
from backend.app.routers.api_key_router import router as api_key_router
from backend.app.routers.audit_router import router as audit_router
from backend.app.routers.auth_router import router as auth_router
from backend.app.routers.ci_router import router as ci_router
from backend.app.routers.finding_router import router as finding_router
from backend.app.routers.github_webhook_router import router as github_webhook_router
from backend.app.routers.health_router import router as health_router
from backend.app.routers.model_router import router as model_router
from backend.app.routers.notification_router import router as notification_router
from backend.app.routers.organization_router import router as organization_router
from backend.app.routers.project_router import router as project_router
from backend.app.routers.remediation_router import router as remediation_router
from backend.app.routers.report_router import router as report_router
from backend.app.routers.repository_router import router as repository_router
from backend.app.routers.result_router import router as result_router
from backend.app.routers.scan_router import router as scan_router
from backend.app.routers.snapshot_router import router as snapshot_router
from backend.app.routers.team_router import invitation_router
from backend.app.routers.team_router import router as team_router
from backend.app.routers.upload_router import router as upload_router
from backend.app.routers.websocket_router import router as websocket_router
from backend.app.routers.xai_router import router as xai_router

__all__ = [
    "analytics_router",
    "api_key_router",
    "audit_router",
    "auth_router",
    "ci_router",
    "finding_router",
    "github_webhook_router",
    "health_router",
    "invitation_router",
    "model_router",
    "notification_router",
    "organization_router",
    "project_router",
    "remediation_router",
    "report_router",
    "repository_router",
    "result_router",
    "scan_router",
    "snapshot_router",
    "team_router",
    "upload_router",
    "websocket_router",
    "xai_router",
]
