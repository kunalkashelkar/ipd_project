# ============================================================
# Database Initialization — Table creation & seed data
# ============================================================

from __future__ import annotations

from backend.app.core.logging import logger
from backend.app.database.base import Base
from backend.app.database.session import engine


async def init_db() -> None:
    """Create all tables from Base metadata.

    Used during development. In production, use Alembic migrations.
    """
    # Import all models so they are registered on Base.metadata
    import backend.app.models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database tables created successfully")


async def seed_admin_user() -> None:
    """Create a default admin user if none exists.

    Only runs in development mode.
    """
    from backend.app.core.config import get_settings
    from backend.app.core.security import hash_password
    from backend.app.database.session import async_session_factory
    from backend.app.models.user import User

    settings = get_settings()
    if not settings.is_development:
        return

    async with async_session_factory() as session:
        from sqlalchemy import select

        result = await session.execute(
            select(User).where(User.role == "admin").limit(1)
        )
        admin = result.scalar_one_or_none()

        if admin is None:
            admin_user = User(
                name="Admin",
                email="admin@vulnscan.local",
                password_hash=hash_password("admin123"),
                role="admin",
                status="active",
            )
            session.add(admin_user)
            await session.commit()
            logger.info("Default admin user created: admin@vulnscan.local")
        else:
            logger.info("Admin user already exists, skipping seed")
