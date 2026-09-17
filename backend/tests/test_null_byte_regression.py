# ============================================================
# Regression Test: Embedded Null Byte on In-Memory Archive Extraction
# ============================================================

import io
import zipfile
import pytest
from pathlib import Path

from backend.app.core.exceptions import ValidationError
from backend.app.utils.zip_utils import safe_extract_zip


def _build_zip_bytes(files: dict[str, str | bytes]) -> bytes:
    """Helper to construct in-memory ZIP bytes."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            if isinstance(content, str):
                content = content.encode("utf-8")
            zf.writestr(name, content)
    return buf.getvalue()


def test_safe_extract_zip_from_bytes_no_null_byte_error(tmp_path: Path):
    """Verify safe_extract_zip extracts raw bytes without 'embedded null byte' ValueError."""
    # Standard ZIP bytes have null bytes in magic headers (PK\x03\x04\x14\x00...)
    archive_bytes = _build_zip_bytes({
        "main.py": "def hello():\n    return 'world'\n",
        "nested/helper.py": "# helper module\n",
    })

    dest_dir = tmp_path / "extracted_source"
    safe_extract_zip(archive_bytes, dest_dir)

    assert (dest_dir / "main.py").exists()
    assert (dest_dir / "main.py").read_text(encoding="utf-8") == "def hello():\n    return 'world'\n"
    assert (dest_dir / "nested" / "helper.py").exists()


def test_safe_extract_zip_from_bytesio(tmp_path: Path):
    """Verify safe_extract_zip works when passed an io.BytesIO object directly."""
    archive_bytes = _build_zip_bytes({"config.json": '{"mode": "test"}'})
    bio = io.BytesIO(archive_bytes)

    dest_dir = tmp_path / "extracted_bio"
    safe_extract_zip(bio, dest_dir)

    assert (dest_dir / "config.json").exists()
    assert (dest_dir / "config.json").read_text(encoding="utf-8") == '{"mode": "test"}'


def test_safe_extract_zip_bytes_rejects_corrupted_data(tmp_path: Path):
    """Verify corrupted bytes raise ValidationError rather than unhandled crash."""
    corrupt_bytes = b"NOT_A_ZIP_FILE_RANDOM_DATA"
    dest_dir = tmp_path / "bad_extract"

    with pytest.raises(ValidationError, match="Invalid or corrupt ZIP file"):
        safe_extract_zip(corrupt_bytes, dest_dir)


def test_safe_extract_zip_bytes_enforces_zip_slip_defense(tmp_path: Path):
    """Verify zip-slip path traversal detection remains active for in-memory bytes."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("../evil.sh", "echo pwned")
    malicious_bytes = buf.getvalue()

    dest_dir = tmp_path / "safe_extract"
    with pytest.raises(ValidationError, match="Path traversal detected"):
        safe_extract_zip(malicious_bytes, dest_dir)


def test_safe_extract_zip_bytes_enforces_max_size(tmp_path: Path):
    """Verify uncompressed size limits are honored when extracting from bytes."""
    archive_bytes = _build_zip_bytes({"large.txt": "A" * 10000})
    dest_dir = tmp_path / "size_extract"

    with pytest.raises(ValidationError, match="exceeds maximum uncompressed size"):
        safe_extract_zip(archive_bytes, dest_dir, max_size=1024)
