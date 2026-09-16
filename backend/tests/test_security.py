# ============================================================
# Security Tests — Archive Traversal, Zip-Slip, and Path Safety
# ============================================================

import io
import zipfile
from pathlib import Path
import pytest

from backend.app.core.exceptions import ValidationError
from backend.app.utils.zip_utils import safe_extract_zip


def _create_zip_with_entries(entries: dict[str, bytes]) -> Path:
    """Helper to create an in-memory zip file and write to disk."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    buf.seek(0)
    return buf


def test_zip_slip_traversal_relative_rejected(tmp_path: Path):
    """Test archive member with relative path traversal (../) is rejected."""
    zip_buf = _create_zip_with_entries({"../../evil.py": b"malicious_code()"})
    zip_file = tmp_path / "traversal.zip"
    zip_file.write_bytes(zip_buf.getvalue())

    dest_dir = tmp_path / "extracted"

    with pytest.raises(ValidationError, match="Path traversal detected"):
        safe_extract_zip(zip_file, dest_dir)


def test_zip_slip_absolute_path_rejected(tmp_path: Path):
    """Test archive member with absolute path is rejected."""
    zip_buf = _create_zip_with_entries({"/etc/passwd": b"root:x:0:0"})
    zip_file = tmp_path / "absolute.zip"
    zip_file.write_bytes(zip_buf.getvalue())

    dest_dir = tmp_path / "extracted"

    with pytest.raises(ValidationError, match="Path traversal detected"):
        safe_extract_zip(zip_file, dest_dir)


def test_zip_slip_windows_drive_rejected(tmp_path: Path):
    """Test archive member with Windows drive specifier (C:) is rejected."""
    zip_buf = _create_zip_with_entries({"C:/Windows/System32/calc.exe": b"evil"})
    zip_file = tmp_path / "drive.zip"
    zip_file.write_bytes(zip_buf.getvalue())

    dest_dir = tmp_path / "extracted"

    with pytest.raises(ValidationError, match="Suspicious path"):
        safe_extract_zip(zip_file, dest_dir)


def test_zip_slip_unc_path_rejected(tmp_path: Path):
    """Test archive member with UNC path (//server/share) is rejected."""
    zip_buf = _create_zip_with_entries({"//malicious.server/share/file.txt": b"evil"})
    zip_file = tmp_path / "unc.zip"
    zip_file.write_bytes(zip_buf.getvalue())

    dest_dir = tmp_path / "extracted"

    with pytest.raises(ValidationError, match="Suspicious path"):
        safe_extract_zip(zip_file, dest_dir)


def test_zip_bomb_size_limit_enforced(tmp_path: Path):
    """Test that archive exceeding max_size triggers ValidationError."""
    # Create 10KB file but set limit to 5KB
    zip_buf = _create_zip_with_entries({"large.txt": b"A" * 10240})
    zip_file = tmp_path / "large.zip"
    zip_file.write_bytes(zip_buf.getvalue())

    dest_dir = tmp_path / "extracted"

    with pytest.raises(ValidationError, match="maximum uncompressed size limit"):
        safe_extract_zip(zip_file, dest_dir, max_size=5120)


def test_zip_bomb_file_count_enforced(tmp_path: Path):
    """Test that archive exceeding max_files triggers ValidationError."""
    entries = {f"file_{i}.txt": b"test" for i in range(15)}
    zip_buf = _create_zip_with_entries(entries)
    zip_file = tmp_path / "many_files.zip"
    zip_file.write_bytes(zip_buf.getvalue())

    dest_dir = tmp_path / "extracted"

    with pytest.raises(ValidationError, match="entry count"):
        safe_extract_zip(zip_file, dest_dir, max_files=10)


def test_valid_zip_extraction(tmp_path: Path):
    """Test legitimate ZIP archive extracts cleanly inside the destination directory."""
    entries = {
        "src/main.py": b"print('hello world')",
        "README.md": b"# Test Project",
    }
    zip_buf = _create_zip_with_entries(entries)
    zip_file = tmp_path / "valid.zip"
    zip_file.write_bytes(zip_buf.getvalue())

    dest_dir = tmp_path / "extracted"
    safe_extract_zip(zip_file, dest_dir)

    assert (dest_dir / "src/main.py").exists()
    assert (dest_dir / "src/main.py").read_text() == "print('hello world')"
    assert (dest_dir / "README.md").exists()
