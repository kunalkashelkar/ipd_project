# ============================================================
# Database Configuration — SQLAlchemy Async Engine
# ============================================================
# Provides the async engine, session factory, and base model
# for all ORM models in the project.
# ============================================================

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from backend.app.config import get_settings

settings = get_settings()

# ── Async Engine ───────────────────────────────────────────
engine = create_async_engine(
    settings.database_url,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    echo=settings.db_echo_sql,
    future=True,
)

# ── Session Factory ────────────────────────────────────────
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ── Base Model ─────────────────────────────────────────────
class Base(DeclarativeBase):
    """Declarative base for all ORM models."""

    pass


# ── Dependency ─────────────────────────────────────────────
async def get_db() -> AsyncSession:
    """FastAPI dependency that yields an async database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ── Table Initialization (development convenience) ─────────
async def init_db() -> None:
    """Create all tables from Base metadata.

    Used during development. In production, prefer Alembic migrations.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
