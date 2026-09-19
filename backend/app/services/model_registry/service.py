# ============================================================
# Model Registry Service (Phase 6)
# ============================================================
# Manages registered AI models, versions, activation status,
# checksum verification, and provenance.
# ============================================================

from __future__ import annotations

import hashlib
import hmac
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import ModelIntegrityError, NotFoundError, ValidationError
from backend.app.models.model_registry import ModelVersion


class ModelRegistryService:
    """Authoritative registry for AI models, weights, and runtimes."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def register_model(
        self,
        *,
        model_name: str,
        version: str,
        provider: str,
        runtime: str = "mock",
        artifact_uri: str | None = None,
        checksum: str | None = None,
        input_schema_version: str = "v1.0.0",
        output_schema_version: str = "v1.0.0",
        status: str = "inactive",
        metadata: dict[str, Any] | None = None,
    ) -> ModelVersion:
        """Register a new model version. Rejects duplicate (model_name, version)."""
        existing = await self.get_by_name_and_version(model_name, version)
        if existing:
            raise ValidationError(f"Model '{model_name}' with version '{version}' is already registered.")

        mv = ModelVersion(
            id=uuid.uuid4(),
            model_name=model_name.strip(),
            version=version.strip(),
            provider=provider.strip(),
            runtime=runtime.strip(),
            artifact_uri=artifact_uri,
            checksum=checksum,
            input_schema_version=input_schema_version,
            output_schema_version=output_schema_version,
            status=status,
            metadata_json=metadata or {},
            created_at=datetime.now(timezone.utc),
            activated_at=datetime.now(timezone.utc) if status == "active" else None,
        )
        self.db.add(mv)
        await self.db.commit()
        await self.db.refresh(mv)
        return mv

    async def activate_model(self, model_version_id: uuid.UUID) -> ModelVersion:
        """Activate a model version and deactivate other versions of the same model_name."""
        mv = await self.db.get(ModelVersion, model_version_id)
        if not mv:
            raise NotFoundError(f"ModelVersion '{model_version_id}' not found.")

        # Deactivate other versions of the same model
        stmt = select(ModelVersion).where(
            ModelVersion.model_name == mv.model_name,
            ModelVersion.id != mv.id,
            ModelVersion.status == "active",
        )
        res = await self.db.execute(stmt)
        for other in res.scalars().all():
            other.status = "inactive"

        mv.status = "active"
        mv.activated_at = datetime.now(timezone.utc)
        mv.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(mv)
        return mv

    async def deactivate_model(self, model_version_id: uuid.UUID) -> ModelVersion:
        """Deactivate a model version."""
        mv = await self.db.get(ModelVersion, model_version_id)
        if not mv:
            raise NotFoundError(f"ModelVersion '{model_version_id}' not found.")

        mv.status = "inactive"
        mv.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(mv)
        return mv

    async def get_active_model(self, model_name: str) -> ModelVersion | None:
        """Get currently active version for a given model name."""
        stmt = (
            select(ModelVersion)
            .where(ModelVersion.model_name == model_name, ModelVersion.status == "active")
            .order_by(ModelVersion.activated_at.desc())
            .limit(1)
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_name_and_version(self, model_name: str, version: str) -> ModelVersion | None:
        """Lookup specific model version."""
        stmt = select(ModelVersion).where(
            ModelVersion.model_name == model_name, ModelVersion.version == version
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def list_models(
        self, *, status: str | None = None, provider: str | None = None
    ) -> list[ModelVersion]:
        """List registered models with optional status/provider filtering."""
        stmt = select(ModelVersion).order_by(ModelVersion.model_name, ModelVersion.version.desc())
        if status:
            stmt = stmt.where(ModelVersion.status == status)
        if provider:
            stmt = stmt.where(ModelVersion.provider == provider)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def verify_artifact_integrity(self, model_version_id: uuid.UUID) -> bool:
        """Verify the SHA-256 checksum of the registered model artifact before loading.

        Enforces fail-closed security:
        - If artifact_uri is missing and runtime is not mock, raises ModelIntegrityError.
        - If registered checksum is provided, computes file SHA-256 and compares.
        - If checksums mismatch, raises ModelIntegrityError.
        """
        mv = await self.db.get(ModelVersion, model_version_id)
        if not mv:
            raise NotFoundError(f"ModelVersion '{model_version_id}' not found.")

        if not mv.artifact_uri:
            if mv.runtime in ("mock", "development"):
                return True
            raise ModelIntegrityError(f"MODEL_INTEGRITY_FAILURE: Model version '{mv.version}' has no artifact URI.")

        path = Path(mv.artifact_uri)
        if not path.is_file():
            raise ModelIntegrityError(f"MODEL_INTEGRITY_FAILURE: Model file not found at '{mv.artifact_uri}'.")

        if mv.checksum:
            h = hashlib.sha256()
            with open(path, "rb") as f:
                while chunk := f.read(65536):
                    h.update(chunk)
            computed = h.hexdigest()
            if not hmac.compare_digest(computed.lower(), mv.checksum.lower()):
                raise ModelIntegrityError(
                    f"MODEL_INTEGRITY_FAILURE: Model '{mv.model_name}:{mv.version}' checksum mismatch. "
                    f"Expected {mv.checksum}, got {computed}."
                )
        return True

