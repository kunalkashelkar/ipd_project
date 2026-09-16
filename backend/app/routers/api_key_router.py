# ============================================================
# Phase 2 API Keys Router
# ============================================================

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request, status

from backend.app.core.authorization import get_current_user, require_permission
from backend.app.core.response import success_response
from backend.app.database.session import AsyncSession, get_db
from backend.app.models.organization import Organization, OrganizationMember
from backend.app.models.user import User
from backend.app.schemas.phase2_schemas import (
    ApiKeyCreatedResponse,
    ApiKeyMetadataResponse,
    CreateApiKeyRequest,
)
from backend.app.services.api_key_service import ApiKeyService

router = APIRouter(prefix="/organizations/{organization_id}/api-keys", tags=["API Keys"])


def _get_client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


@router.post("", summary="Create a new API key", status_code=status.HTTP_201_CREATED)
async def create_api_key(
    organization_id: uuid.UUID,
    body: CreateApiKeyRequest,
    request: Request,
    org_context: tuple[Organization, OrganizationMember] = Depends(require_permission("api_key.create")),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate an API key for the organization. The plaintext secret is returned ONLY ONCE."""
    service = ApiKeyService(db)
    api_key, full_secret = await service.create_key(
        org_id=organization_id,
        user_id=current_user.id,
        name=body.name,
        expires_in_days=body.expires_in_days,
        ip_address=_get_client_ip(request),
    )

    return success_response(
        data=ApiKeyCreatedResponse(
            id=api_key.id,
            name=api_key.name,
            key_prefix=api_key.key_prefix,
            api_key=full_secret,
            expires_at=api_key.expires_at,
            created_at=api_key.created_at,
        ).model_dump(mode="json"),
        message="API key created successfully",
        status_code=201,
    )


@router.get("", summary="List API keys for the organization")
async def list_api_keys(
    organization_id: uuid.UUID,
    org_context: tuple[Organization, OrganizationMember] = Depends(require_permission("api_key.read")),
    db: AsyncSession = Depends(get_db),
):
    """List metadata for active and revoked API keys (never exposes secrets)."""
    service = ApiKeyService(db)
    keys = await service.list_keys(organization_id)

    return success_response(
        data=[
            ApiKeyMetadataResponse.model_validate(k).model_dump(mode="json")
            for k in keys
        ],
        message="API keys retrieved",
    )


@router.delete("/{key_id}", summary="Revoke an API key")
async def revoke_api_key(
    organization_id: uuid.UUID,
    key_id: uuid.UUID,
    request: Request,
    org_context: tuple[Organization, OrganizationMember] = Depends(require_permission("api_key.revoke")),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke an active API key immediately."""
    service = ApiKeyService(db)
    await service.revoke_key(
        key_id=key_id,
        org_id=organization_id,
        user_id=current_user.id,
        ip_address=_get_client_ip(request),
    )
    return success_response(data=None, message="API key revoked")
