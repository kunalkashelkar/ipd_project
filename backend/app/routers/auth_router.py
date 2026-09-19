# ============================================================
# Phase 2 Auth Router — Registration, Login, Sessions, Tokens
# ============================================================

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from backend.app.core.authorization import get_current_user_and_session
from backend.app.core.rate_limit import RateLimiter
from backend.app.core.response import success_response
from backend.app.database.session import AsyncSession, get_db
from backend.app.models.session import UserSession
from backend.app.models.user import User
from backend.app.schemas.phase2_schemas import (
    EmailVerificationRequest,
    LoginRequest,
    OrganizationResponse,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    RefreshRequest,
    RegisterRequest,
)
from backend.app.schemas.user import UserResponse
from backend.app.services.auth_service import AuthService
from backend.app.services.organization_service import OrganizationService

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _get_client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


@router.post(
    "/register",
    summary="Register user with new organization workspace",
    dependencies=[Depends(RateLimiter(times=10, seconds=60, scope="auth:register"))],
)
async def register(
    body: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user identity and automatically establish a dedicated Organization workspace where user is Owner."""
    service = AuthService(db)
    result = await service.register(
        name=body.name,
        email=body.email,
        password=body.password,
        organization_name=body.organization_name,
        invitation_token=body.invitation_token,
        ip_address=_get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )
    return success_response(
        data={
            "user": UserResponse.model_validate(result["user"]).model_dump(mode="json"),
            "organization": OrganizationResponse.model_validate(result["organization"]).model_dump(mode="json"),
            "tokens": result["tokens"],
        },
        message="User and organization registered successfully",
        status_code=201,
    )


@router.post(
    "/login",
    summary="Login with email and password",
    dependencies=[Depends(RateLimiter(times=15, seconds=60, scope="auth:login"))],
)
async def login(
    body: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate credentials, create server-side session, and return tokens."""
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
            "organizations": [
                OrganizationResponse.model_validate(o).model_dump(mode="json")
                for o in result["organizations"]
            ],
            "active_organization": (
                OrganizationResponse.model_validate(result["active_organization"]).model_dump(mode="json")
                if result["active_organization"]
                else None
            ),
            "tokens": result["tokens"],
        },
        message="Login successful",
    )


@router.post("/logout", summary="Logout and revoke server session")
async def logout(
    request: Request,
    auth_data: tuple[User, UserSession | None] = Depends(get_current_user_and_session),
    db: AsyncSession = Depends(get_db),
):
    """Revoke the current server-side session."""
    user, session = auth_data
    service = AuthService(db)
    await service.logout(
        session_id=session.id if session else None,
        user_id=user.id,
        ip_address=_get_client_ip(request),
    )
    return success_response(message="Logged out successfully; session revoked")


@router.post(
    "/refresh",
    summary="Refresh session and rotate token",
    dependencies=[Depends(RateLimiter(times=45, seconds=60, scope="auth:refresh"))],
)
async def refresh_token(
    body: RefreshRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Rotate refresh token and issue new access token from active server session."""
    service = AuthService(db)
    result = await service.refresh_session(
        raw_refresh_token=body.refresh_token,
        user_agent=request.headers.get("User-Agent"),
        ip_address=_get_client_ip(request),
    )
    return success_response(
        data={
            "user": UserResponse.model_validate(result["user"]).model_dump(mode="json"),
            "tokens": result["tokens"],
        },
        message="Session refreshed successfully",
    )


@router.get("/me", summary="Get current authenticated user and organizations")
async def get_me(
    request: Request,
    auth_data: tuple[User, UserSession | None] = Depends(get_current_user_and_session),
    db: AsyncSession = Depends(get_db),
):
    """Return identity and accessible organizations for authenticated user."""
    user, _ = auth_data
    org_service = OrganizationService(db)
    orgs = await org_service.list_user_organizations(user.id)

    data = UserResponse.model_validate(user).model_dump(mode="json")
    org_responses = [
        OrganizationResponse.model_validate(o).model_dump(mode="json") for o in orgs
    ]
    data["organizations"] = org_responses

    target_org_header = request.headers.get("X-Organization-ID")
    active_role = None
    if target_org_header:
        for o_dict in org_responses:
            if str(o_dict.get("id")) == target_org_header:
                active_role = o_dict.get("current_user_role")
                break
    if not active_role and org_responses:
        active_role = org_responses[0].get("current_user_role")
    if active_role:
        data["active_organization_role"] = active_role

    return success_response(data=data, message="User profile retrieved")


@router.post(
    "/request-password-reset",
    summary="Request password reset token",
    dependencies=[Depends(RateLimiter(times=10, seconds=60, scope="auth:reset"))],
)
async def request_password_reset(
    body: PasswordResetRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Request a password reset link. Always returns 200 to prevent user enumeration."""
    service = AuthService(db)
    token = await service.request_password_reset(
        email=body.email,
        ip_address=_get_client_ip(request),
    )
    resp = {"message": "If the email is registered, a password reset token has been issued."}
    # In development / test environment, return the token for testing convenience
    if token:
        resp["dev_token"] = token
        resp["reset_url"] = f"/reset-password?token={token}"
    return success_response(data=resp, message="Password reset processed")


@router.post(
    "/reset-password",
    summary="Reset password with valid token",
    dependencies=[Depends(RateLimiter(times=10, seconds=60, scope="auth:reset"))],
)
async def reset_password(
    body: PasswordResetConfirmRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Reset password using one-time token; invalidates all active sessions."""
    service = AuthService(db)
    await service.reset_password(
        raw_token=body.token,
        new_password=body.new_password,
        ip_address=_get_client_ip(request),
    )
    return success_response(message="Password reset successful. All active sessions invalidated.")


@router.post(
    "/verify-email",
    summary="Verify email address",
    dependencies=[Depends(RateLimiter(times=20, seconds=60, scope="auth:verify"))],
)
async def verify_email(
    body: EmailVerificationRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Consume email verification token."""
    service = AuthService(db)
    await service.verify_email(
        raw_token=body.token,
        ip_address=_get_client_ip(request),
    )
    return success_response(message="Email verified successfully")
