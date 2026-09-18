# ============================================================
# Main Application Entrypoint — FastAPI
# ============================================================

from __future__ import annotations

import sys
from pathlib import Path

# Ensure repository root is in sys.path for seamless execution from any CWD
_PROJECT_ROOT = str(Path(__file__).resolve().parents[2])
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from backend.app.core.config import get_settings
from backend.app.core.logging import logger, setup_logging
from backend.app.middleware.error_handler import register_exception_handlers
from backend.app.middleware.request_id import RequestIDMiddleware
from backend.app.routers import (
    analytics_router,
    api_key_router,
    audit_router,
    auth_router,
    finding_router,
    health_router,
    invitation_router,
    model_router,
    notification_router,
    organization_router,
    project_router,
    remediation_router,
    report_router,
    repository_router,
    result_router,
    scan_router,
    snapshot_router,
    team_router,
    upload_router,
    websocket_router,
    xai_router,
)



settings = get_settings()


# ── Lifespan ───────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup / shutdown lifecycle."""
    # ── Startup ────────────────────────────────────────────
    setup_logging(log_level=settings.log_level, log_dir=settings.log_dir)
    logger.info(
        "Starting {name} in {env} mode",
        name=settings.app_name,
        env=settings.app_env,
    )

    # Schema is managed authoritatively via Alembic migrations.
    # Base.metadata.create_all() has been removed from normal startup.

    yield

    # ── Shutdown ───────────────────────────────────────────
    logger.info("Shutting down {name}", name=settings.app_name)


# ── App Factory ────────────────────────────────────────────

app = FastAPI(
    title=settings.app_name,
    description="Backend API for the AI-Ready Vulnerability Detection Framework.",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ── Middleware ─────────────────────────────────────────────
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
register_exception_handlers(app)

# ── Routers ────────────────────────────────────────────────
API_PREFIX = "/api/v1"

# Batch 1: Identity & System
app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(invitation_router, prefix=API_PREFIX)
app.include_router(health_router)

# Batch 2: Organizations & RBAC
app.include_router(organization_router, prefix=API_PREFIX)
app.include_router(team_router, prefix=API_PREFIX)
app.include_router(api_key_router, prefix=API_PREFIX)
app.include_router(audit_router, prefix=API_PREFIX)

# Batch 3: Projects, Repositories, Snapshots & Scans
app.include_router(project_router, prefix=API_PREFIX)
app.include_router(repository_router, prefix=API_PREFIX)
app.include_router(snapshot_router, prefix=API_PREFIX)
app.include_router(upload_router, prefix=API_PREFIX)
app.include_router(scan_router, prefix=API_PREFIX)

# Batch 4: Results, Findings & Reports
app.include_router(finding_router, prefix=API_PREFIX)
app.include_router(result_router, prefix=API_PREFIX)
app.include_router(report_router, prefix=API_PREFIX)

# Batch 5: Phase 6 XAI, Remediation & Model Registry
app.include_router(xai_router, prefix=API_PREFIX)
app.include_router(remediation_router, prefix=API_PREFIX)
app.include_router(model_router, prefix=API_PREFIX)

# Batch 6: Notifications, Analytics & WebSockets
app.include_router(websocket_router)
app.include_router(notification_router, prefix=API_PREFIX)
app.include_router(analytics_router, prefix=API_PREFIX)




# ── Root redirect ──────────────────────────────────────────

@app.get("/", include_in_schema=False)
async def root():
    """Redirect root to API docs."""
    return RedirectResponse(url="/docs")


# ── Run directly ───────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.app.main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=settings.backend_reload,
        workers=settings.backend_workers,
    )
