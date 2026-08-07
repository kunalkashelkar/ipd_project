# ============================================================
# Role-Based Access Control — FastAPI Dependencies
# ============================================================
# Provides injectable dependencies for authentication and
# authorization. Endpoints declare what they need:
#
#   current_user = Depends(get_current_active_user)
#   admin_user   = Depends(require_admin)
# ============================================================

from __future__ import annotations

import uuid

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.app.core.exceptions import AuthenticationError, AuthorizationError
from backend.app.core.security import decode_token
from backend.app.database.session import AsyncSession, get_db

security_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
):
    """Extract and validate the current user from the Bearer token.

    Returns the User ORM object.
    """
    if credentials is None:
        raise AuthenticationError("Missing authentication token")

    payload = decode_token(credentials.credentials)

    if payload.get("type") != "access":
        raise AuthenticationError("Invalid token type — expected access token")

    user_id = payload.get("sub")
    if user_id is None:
        raise AuthenticationError("Invalid token payload")

    # Import here to avoid circular imports
    from backend.app.repositories.user_repository import UserRepository

    repo = UserRepository(db)
    user = await repo.get_by_id(uuid.UUID(user_id))
    if user is None:
        raise AuthenticationError("User not found")

    return user


async def get_current_active_user(current_user=Depends(get_current_user)):
    """Ensure the current user account is active."""
    if current_user.status != "active":
        raise AuthorizationError("User account is not active")
    return current_user


async def require_admin(current_user=Depends(get_current_active_user)):
    """Require the current user to have admin role."""
    if current_user.role != "admin":
        raise AuthorizationError("Admin access required")
    return current_user


async def require_researcher(current_user=Depends(get_current_active_user)):
    """Require the current user to have researcher or admin role."""
    if current_user.role not in ("admin", "researcher"):
        raise AuthorizationError("Researcher access required")
    return current_user


async def require_project_access(
    project_id: uuid.UUID,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Ensure the current user has access to the specified project.

    Admins can access any project. Other roles must be the project owner.
    """
    from backend.app.repositories.project_repository import ProjectRepository

    repo = ProjectRepository(db)
    project = await repo.get_by_id(project_id)

    if project is None:
        from backend.app.core.exceptions import NotFoundError

        raise NotFoundError(f"Project {project_id} not found")

    if current_user.role == "admin":
        return current_user

    if project.owner_id != current_user.id:
        raise AuthorizationError("You do not have access to this project")

    return current_user
