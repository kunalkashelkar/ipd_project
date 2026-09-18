# ============================================================
# Model Registry Router — AI Models & Provenance (Phase 6)
# ============================================================
# Manages registered AI inference, explanation, and remediation models
# with explicit versioning, checksum tracking, and activation states.
# ============================================================

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.authorization import get_current_user
from backend.app.core.exceptions import AuthorizationError, NotFoundError
from backend.app.core.response import success_response
from backend.app.database.session import get_db
from backend.app.models.user import User
from backend.app.schemas.remediation_schemas import ModelVersionResponse, RegisterModelVersionRequest
from backend.app.services.model_registry.service import ModelRegistryService

router = APIRouter(tags=["Model Registry"])


@router.get("/models", summary="List registered models")
async def list_models(
    runtime: str | None = Query(None, description="Filter by runtime (pytorch, onnx, api, mock)"),
    status: str | None = Query(None, description="Filter by status (active, inactive, deprecated)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all registered AI inference and remediation models."""
    service = ModelRegistryService(db)
    models = await service.list_models(runtime=runtime, status=status)
    items = [ModelVersionResponse.model_validate(m).model_dump(mode="json") for m in models]
    return success_response(data=items, message=f"Retrieved {len(items)} model version(s)")


@router.get("/models/{model_name}/versions", summary="List versions of a model")
async def list_model_versions(
    model_name: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve all versions and statuses for a named model."""
    service = ModelRegistryService(db)
    models = await service.list_models()
    matching = [m for m in models if m.model_name == model_name]
    items = [ModelVersionResponse.model_validate(m).model_dump(mode="json") for m in matching]
    return success_response(data=items, message=f"Retrieved {len(items)} version(s) for '{model_name}'")


@router.post("/models", summary="Register model version")
async def register_model(
    body: RegisterModelVersionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Register a new AI model version preserving immutable provenance."""
    service = ModelRegistryService(db)
    model = await service.register_model_version(
        model_name=body.model_name,
        version=body.version,
        provider=body.provider,
        artifact_uri=body.artifact_uri,
        checksum=body.checksum,
        runtime=body.runtime,
        input_schema_version=body.input_schema_version,
        output_schema_version=body.output_schema_version,
        metadata_json=body.metadata_json,
    )
    return success_response(
        data=ModelVersionResponse.model_validate(model).model_dump(mode="json"),
        message=f"Model version '{body.model_name}:{body.version}' registered",
    )


@router.post("/models/{model_id}/activate", summary="Activate model version")
async def activate_model(
    model_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Activate a model version for production inference."""
    service = ModelRegistryService(db)
    model = await service.activate_model_version(model_id)
    return success_response(
        data=ModelVersionResponse.model_validate(model).model_dump(mode="json"),
        message=f"Model version '{model.model_name}:{model.version}' activated",
    )


@router.post("/models/{model_id}/deactivate", summary="Deactivate model version")
async def deactivate_model(
    model_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Deactivate a model version."""
    service = ModelRegistryService(db)
    model = await service.deactivate_model_version(model_id)
    return success_response(
        data=ModelVersionResponse.model_validate(model).model_dump(mode="json"),
        message=f"Model version '{model.model_name}:{model.version}' deactivated",
    )
