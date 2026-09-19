# ============================================================
# Storage Service — High-level Domain Storage Abstraction
# ============================================================

from __future__ import annotations

import uuid
from pathlib import Path

from backend.app.core.config import get_settings
from backend.app.core.exceptions import StorageError
from backend.app.storage.base import StorageBackend
from backend.app.storage.local_storage import LocalStorage
from backend.app.storage.s3_storage import S3Storage


class StorageService:
    """Unified storage service decoupling application logic from physical storage."""

    def __init__(self, backend: StorageBackend | None = None):
        settings = get_settings()
        if backend is not None:
            self.backend = backend
        elif settings.storage_backend in ("s3", "minio"):
            self.backend = S3Storage()
        elif settings.storage_backend == "local":
            self.backend = LocalStorage()
        else:
            raise StorageError(f"Unsupported storage backend: {settings.storage_backend}")

    # ── Snapshot Key Generation Helpers (Tenant-Scoped) ──────

    @staticmethod
    def snapshot_archive_key(
        org_id: uuid.UUID, project_id: uuid.UUID, snapshot_id: uuid.UUID, ext: str = ".zip"
    ) -> str:
        """organizations/{org_id}/projects/{project_id}/snapshots/{snapshot_id}/archive{ext}"""
        clean_ext = ext if ext.startswith(".") else f".{ext}"
        return f"organizations/{org_id}/projects/{project_id}/snapshots/{snapshot_id}/archive{clean_ext}"

    @staticmethod
    def snapshot_manifest_key(
        org_id: uuid.UUID, project_id: uuid.UUID, snapshot_id: uuid.UUID
    ) -> str:
        """organizations/{org_id}/projects/{project_id}/snapshots/{snapshot_id}/manifest.json"""
        return f"organizations/{org_id}/projects/{project_id}/snapshots/{snapshot_id}/manifest.json"

    @staticmethod
    def snapshot_file_key(
        org_id: uuid.UUID,
        project_id: uuid.UUID,
        snapshot_id: uuid.UUID,
        relative_path: str,
        kind: str = "original",
    ) -> str:
        """organizations/{org_id}/projects/{project_id}/snapshots/{snapshot_id}/{kind}/{relative_path}"""
        clean_rel = relative_path.replace("\\", "/").lstrip("/")
        return f"organizations/{org_id}/projects/{project_id}/snapshots/{snapshot_id}/{kind}/{clean_rel}"

    @staticmethod
    def scan_artifact_key(
        org_id: uuid.UUID,
        project_id: uuid.UUID,
        scan_id: uuid.UUID,
        artifact_type: str,
        artifact_id: uuid.UUID,
        ext: str = ".json",
    ) -> str:
        """organizations/{org_id}/projects/{project_id}/scans/{scan_id}/artifacts/{artifact_type}/{artifact_id}{ext}"""
        clean_ext = ext if ext.startswith(".") else f".{ext}"
        clean_type = artifact_type.lower()
        return f"organizations/{org_id}/projects/{project_id}/scans/{scan_id}/artifacts/{clean_type}/{artifact_id}{clean_ext}"

    @staticmethod
    def xai_artifact_key(
        org_id: uuid.UUID,
        project_id: uuid.UUID,
        finding_id: uuid.UUID,
        explanation_id: uuid.UUID,
        ext: str = ".json",
    ) -> str:
        """organizations/{org_id}/projects/{project_id}/findings/{finding_id}/xai/{explanation_id}{ext}"""
        clean_ext = ext if ext.startswith(".") else f".{ext}"
        return f"organizations/{org_id}/projects/{project_id}/findings/{finding_id}/xai/{explanation_id}{clean_ext}"

    @staticmethod
    def remediation_patch_key(
        org_id: uuid.UUID,
        project_id: uuid.UUID,
        finding_id: uuid.UUID,
        remediation_id: uuid.UUID,
        ext: str = ".diff",
    ) -> str:
        """organizations/{org_id}/projects/{project_id}/findings/{finding_id}/remediations/{remediation_id}/patch{ext}"""
        clean_ext = ext if ext.startswith(".") else f".{ext}"
        return f"organizations/{org_id}/projects/{project_id}/findings/{finding_id}/remediations/{remediation_id}/patch{clean_ext}"

    @staticmethod
    def validation_logs_key(
        org_id: uuid.UUID,
        project_id: uuid.UUID,
        remediation_id: uuid.UUID,
        validation_id: uuid.UUID,
        ext: str = ".txt",
    ) -> str:
        """organizations/{org_id}/projects/{project_id}/remediations/{remediation_id}/validations/{validation_id}/logs{ext}"""
        clean_ext = ext if ext.startswith(".") else f".{ext}"
        return f"organizations/{org_id}/projects/{project_id}/remediations/{remediation_id}/validations/{validation_id}/logs{clean_ext}"

    @staticmethod
    def report_file_key(
        org_id: uuid.UUID,
        project_id: uuid.UUID,
        report_public_id: str,
        format: str,
    ) -> str:
        """organizations/{org_id}/projects/{project_id}/reports/{report_public_id}/report.{format}"""
        clean_fmt = format.lower().lstrip(".")
        return f"organizations/{org_id}/projects/{project_id}/reports/{report_public_id}/report.{clean_fmt}"

    # ── Storage Operations ──────────────────────────────────

    async def save_upload(
        self,
        *,
        project_id: uuid.UUID,
        upload_id: uuid.UUID,
        file_extension: str,
        content: bytes,
    ) -> str:
        """Store an uploaded file under an unguessable, safe generated path."""
        clean_ext = file_extension.strip()
        if not clean_ext.startswith("."):
            clean_ext = f".{clean_ext}"

        safe_path = f"uploads/{project_id}/{upload_id}{clean_ext}"
        return await self.backend.store(content, safe_path)

    async def save_object(self, content: bytes, path: str) -> str:
        """Store content at a specified key."""
        return await self.backend.store(content, path)

    async def read_file(self, stored_path: str) -> bytes:
        """Retrieve stored content safely."""
        return await self.backend.retrieve(stored_path)

    async def delete_file(self, stored_path: str) -> bool:
        """Delete stored content safely."""
        return await self.backend.delete(stored_path)

    async def get_access_url(self, stored_path: str) -> str:
        """Get an access URI or URL for the stored artifact."""
        return await self.backend.get_url(stored_path)

    async def object_exists(self, stored_path: str) -> bool:
        """Check if an object exists."""
        return await self.backend.object_exists(stored_path)

    async def head_object(self, stored_path: str) -> dict | None:
        """Get object metadata."""
        return await self.backend.head_object(stored_path)

    async def generate_download_url(self, stored_path: str, expires_in_seconds: int = 3600) -> str:
        """Generate a secure, time-limited presigned download reference."""
        return await self.backend.generate_download_reference(stored_path, expires_in_seconds)
