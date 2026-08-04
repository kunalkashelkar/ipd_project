# ============================================================
# Upload Router — File Upload with Validation
# ============================================================
# Accepts C, C++, and ZIP files.
# Validates extension, file size, and duplicate content (SHA-256).
# ============================================================

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile
from loguru import logger

from backend.app.config import get_settings
from backend.app.schemas import MessageResponse, UploadListResponse, UploadResponse

router = APIRouter(prefix="/upload", tags=["Uploads"])

# ── In-memory tracking (placeholder until DB wired) ────────
_uploads: dict[uuid.UUID, UploadResponse] = {}
_content_hashes: set[str] = set()


def _validate_extension(filename: str, allowed: list[str]) -> str:
    """Return the lowercased extension or raise 400."""
    ext = Path(filename).suffix.lower()
    if ext not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"File extension '{ext}' not allowed. Accepted: {allowed}",
        )
    return ext


def _compute_hash(data: bytes) -> str:
    """Return SHA-256 hex digest of file content."""
    return hashlib.sha256(data).hexdigest()


@router.post(
    "",
    response_model=UploadResponse,
    status_code=201,
    summary="Upload a source file",
    description="Upload a C, C++, or ZIP file for vulnerability analysis.",
)
async def upload_file(
    file: UploadFile,
    project_id: uuid.UUID | None = None,
) -> UploadResponse:
    settings = get_settings()

    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided.")

    # 1. Validate extension
    ext = _validate_extension(file.filename, settings.allowed_extension_list)

    # 2. Read content & validate size
    content = await file.read()
    if len(content) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds maximum size of {settings.max_upload_size_mb} MB.",
        )

    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # 3. Check for duplicates via SHA-256
    content_hash = _compute_hash(content)
    if content_hash in _content_hashes:
        raise HTTPException(
            status_code=409,
            detail="Duplicate file detected. This file has already been uploaded.",
        )

    # 4. Store file on disk
    upload_dir = settings.upload_path
    stored_filename = f"{uuid.uuid4().hex}_{file.filename}"
    file_path = upload_dir / stored_filename
    file_path.write_bytes(content)

    # 5. Track
    _content_hashes.add(content_hash)
    upload_id = uuid.uuid4()
    pid = project_id or uuid.uuid4()

    record = UploadResponse(
        id=upload_id,
        project_id=pid,
        filename=stored_filename,
        original_filename=file.filename,
        file_size=len(content),
        file_extension=ext,
        status="validated",
        created_at=datetime.now(timezone.utc),
    )
    _uploads[upload_id] = record

    logger.bind(category="upload").info(
        "File uploaded — id={id} name={name} size={size} ext={ext}",
        id=upload_id,
        name=file.filename,
        size=len(content),
        ext=ext,
    )

    return record


@router.get(
    "",
    response_model=UploadListResponse,
    summary="List uploads",
    description="Returns all uploaded files.",
)
async def list_uploads() -> UploadListResponse:
    uploads = list(_uploads.values())
    return UploadListResponse(uploads=uploads, total=len(uploads))
