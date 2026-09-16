# ============================================================
# Storage Abstraction Tests — Path Containment & Isolation
# ============================================================

import uuid
from pathlib import Path
import pytest

from backend.app.core.exceptions import StorageError
from backend.app.storage.local_storage import LocalStorage
from backend.app.storage.service import StorageService


@pytest.mark.asyncio
async def test_local_storage_store_and_retrieve(tmp_path: Path):
    """Test saving and retrieving files within the storage boundary."""
    backend = LocalStorage(base_dir=tmp_path)
    content = b"sample security artifact content"
    path = "uploads/project-1/file.txt"

    stored_path = await backend.store(content, path)
    assert Path(stored_path).exists()

    retrieved = await backend.retrieve(path)
    assert retrieved == content


@pytest.mark.asyncio
async def test_local_storage_traversal_blocked(tmp_path: Path):
    """Test path traversal attempts outside storage root are blocked."""
    backend = LocalStorage(base_dir=tmp_path)
    content = b"malicious write"

    with pytest.raises(StorageError, match="Path traversal detected"):
        await backend.store(content, "../../outside.txt")


@pytest.mark.asyncio
async def test_storage_service_save_upload(tmp_path: Path):
    """Test high-level StorageService generates safe paths and persists uploads."""
    backend = LocalStorage(base_dir=tmp_path)
    service = StorageService(backend=backend)

    project_id = uuid.uuid4()
    upload_id = uuid.uuid4()
    content = b"source code bytes"

    stored_path = await service.save_upload(
        project_id=project_id,
        upload_id=upload_id,
        file_extension=".zip",
        content=content,
    )

    assert str(project_id) in stored_path
    assert str(upload_id) in stored_path
    assert Path(stored_path).exists()

    read_back = await service.read_file(stored_path)
    assert read_back == content

    # Test delete
    deleted = await service.delete_file(stored_path)
    assert deleted is True
    assert not Path(stored_path).exists()
