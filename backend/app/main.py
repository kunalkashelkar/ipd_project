# ============================================================
# Main Application Entrypoint — FastAPI
# ============================================================
# Run with:
#   uvicorn backend.app.main:app --reload
# or:
#   python -m backend.app.main
# ============================================================

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import get_settings
from backend.app.routers import features_router, health_router, model_router, parser_router, projects_router, semantic_router, taint_router, upload_router
from backend.app.utils.logging import logger, setup_logging


# ── Lifespan ───────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup / shutdown lifecycle."""
    # ── Startup ────────────────────────────────────────────
    setup_logging()
    settings = get_settings()
    logger.info(
        "Starting {name} in {env} mode",
        name=settings.app_name,
        env=settings.app_env,
    )

    # Create upload directory if it doesn't exist
    settings.upload_path.mkdir(parents=True, exist_ok=True)

    # Initialize database tables (dev convenience — use Alembic in prod)
    try:
        from backend.app.database import init_db

        await init_db()
        logger.info("Database tables initialized")
    except Exception as exc:
        logger.warning("Database initialization skipped: {err}", err=str(exc))

    yield

    # ── Shutdown ───────────────────────────────────────────
    logger.info("Shutting down {name}", name=settings.app_name)


# ── App Factory ────────────────────────────────────────────

settings = get_settings()

app = FastAPI(
    title="Hybrid XAI Vulnerability Detection API",
    description=(
        "Backend API for the Hybrid Explainable AI framework for "
        "software vulnerability detection. Combines program analysis "
        "(CPG, taint analysis) with Graph Neural Networks and XAI."
    ),
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ── CORS ───────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────
API_PREFIX = "/api/v1"

app.include_router(health_router, prefix=API_PREFIX)
app.include_router(projects_router, prefix=API_PREFIX)
app.include_router(upload_router, prefix=API_PREFIX)
app.include_router(parser_router, prefix=API_PREFIX)
app.include_router(taint_router, prefix=API_PREFIX)
app.include_router(features_router, prefix=API_PREFIX)
app.include_router(model_router, prefix=API_PREFIX)
app.include_router(semantic_router, prefix=API_PREFIX)


# ── Root redirect ──────────────────────────────────────────


@app.get("/", include_in_schema=False)
async def root():
    """Redirect root to API docs."""
    from fastapi.responses import RedirectResponse

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
