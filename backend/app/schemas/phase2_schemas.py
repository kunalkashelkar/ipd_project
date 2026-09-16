# ============================================================
# Phase 2 Pydantic Schemas: Organizations, Members, RBAC, Keys, Auth
# ============================================================

from __future__ import annotations

import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ── Auth & Identity ─────────────────────────────────────────


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    role: str | None = Field(default=None, pattern="^(researcher|developer)$")
    organization_name: str | None = Field(None, min_length=2, max_length=255)
    invitation_token: str | None = Field(default=None, description="Optional invitation token to register and join an organization directly")



class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class EmailVerificationRequest(BaseModel):
    token: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirmRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)


# ── Organizations ───────────────────────────────────────────


class CreateOrganizationRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    slug: str | None = Field(None, min_length=2, max_length=100)
    description: str | None = None


class UpdateOrganizationRequest(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=255)
    description: str | None = None


class OrganizationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    description: str | None = None
    is_active: bool
    current_user_role: str | None = None
    created_at: datetime
    updated_at: datetime


# ── Team & Memberships ──────────────────────────────────────


class InviteMemberRequest(BaseModel):
    email: EmailStr
    role_name: str = Field(..., pattern="^(admin|security_analyst|developer|viewer)$")


class ChangeMemberRoleRequest(BaseModel):
    role_name: str = Field(..., pattern="^(owner|admin|security_analyst|developer|viewer)$")


class AcceptInvitationRequest(BaseModel):
    token: str
    name: str | None = None
    password: str | None = None


class RoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None = None


class PermissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    key: str
    description: str | None = None
    category: str


class RoleWithPermissionsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None = None
    permissions: list[PermissionResponse] = []


class OrganizationMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    user_name: str
    user_email: str
    role: str
    status: str
    joined_at: datetime


class OrganizationInvitationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    invited_email: str
    role_name: str
    status: str
    expires_at: datetime
    created_at: datetime


# ── API Keys ────────────────────────────────────────────────


class CreateApiKeyRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    expires_in_days: int | None = Field(None, ge=1, le=365)


class ApiKeyCreatedResponse(BaseModel):
    id: uuid.UUID
    name: str
    key_prefix: str
    api_key: str  # Plaintext secret shown ONLY on creation
    expires_at: datetime | None = None
    created_at: datetime


class ApiKeyMetadataResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    key_prefix: str
    last_used_at: datetime | None = None
    expires_at: datetime | None = None
    revoked_at: datetime | None = None
    created_at: datetime


# ── Sessions ────────────────────────────────────────────────


class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_agent: str | None = None
    ip_address: str | None = None
    last_used_at: datetime
    created_at: datetime
    is_current: bool = False
