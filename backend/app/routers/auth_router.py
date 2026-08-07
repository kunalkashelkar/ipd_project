# ============================================================
# Auth Router — Registration, Login, Token Management
# ============================================================

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from backend.app.core.permissions import get_current_active_user
from backend.app.core.response import success_response
from backend.app.database.session import AsyncSession, get_db
from backend.app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from backend.app.schemas.user import UserResponse
from backend.app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _get_client_ip(request: Request) -> str | None:
    """Extract client IP from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


@router.post("/register", summary="Register a new user")
async def register(
    body: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user and return JWT tokens."""
    service = AuthService(db)
    result = await service.register(
        name=body.name,
        email=body.email,
        password=body.password,
        role=body.role,
        ip_address=_get_client_ip(request),
    )
    return success_response(
        data={
            "user": UserResponse.model_validate(result["user"]).model_dump(mode="json"),
            "tokens": result["tokens"],
        },
        message="User registered successfully",
    )


@router.post("/login", summary="Login with email and password")
async def login(
    body: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate user and return JWT tokens."""
    service = AuthService(db)
    result = await service.login(
        email=body.email,
        password=body.password,
        ip_address=_get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )
    return success_response(
        data={
            "user": UserResponse.model_validate(result["user"]).model_dump(mode="json"),
            "tokens": result["tokens"],
        },
        message="Login successful",
    )


@router.post("/logout", summary="Logout")
async def logout(
    request: Request,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Log the user out (audit event)."""
    service = AuthService(db)
    await service.logout(
        user_id=current_user.id,
        ip_address=_get_client_ip(request),
    )
    return success_response(message="Logged out successfully")


@router.post("/refresh", summary="Refresh access token")
async def refresh_token(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    """Issue new token pair from a valid refresh token."""
    service = AuthService(db)
    result = await service.refresh_token(body.refresh_token)
    return success_response(
        data={
            "tokens": result["tokens"],
        },
        message="Token refreshed successfully",
    )


@router.get("/me", summary="Get current user profile")
async def get_me(
    current_user=Depends(get_current_active_user),
):
    """Return the current authenticated user's profile."""
    return success_response(
        data=UserResponse.model_validate(current_user).model_dump(mode="json"),
        message="User profile retrieved",
    )
