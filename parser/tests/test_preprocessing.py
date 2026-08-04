# ============================================================
# Tests — Preprocessing
# ============================================================

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from parser.preprocessing.extractor import ExtractionError, ZIPExtractor
from parser.preprocessing.normalizer import Normalizer
from parser.preprocessing.validator import ProjectValidator, ValidationError


# ── Fixtures ───────────────────────────────────────────────

@pytest.fixture
def tmp_c_project(tmp_path: Path) -> Path:
    """Create a minimal C project with one source and one header file."""
    src = tmp_path / "project"
    src.mkdir()
    (src / "main.c").write_text("int main() { return 0; }\n")
    (src / "utils.h").write_text("void helper();\n")
    (src / "build").mkdir()
    (src / "build" / "output.o").write_bytes(b"\x7fELF")  # binary — should be ignored
    return src


@pytest.fixture
def tmp_zip(tmp_path: Path, tmp_c_project: Path) -> Path:
    """Package the C project into a ZIP archive."""
    archive = tmp_path / "project.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        for f in tmp_c_project.rglob("*"):
            zf.write(f, f.relative_to(tmp_c_project.parent))
    return archive


# ── ProjectValidator tests ─────────────────────────────────

class TestProjectValidator:

    def test_discovers_c_files(self, tmp_c_project: Path) -> None:
        meta = ProjectValidator().validate(tmp_c_project)
        assert meta.file_count == 2
        assert meta.language == "C"

    def test_ignores_build_dir(self, tmp_c_project: Path) -> None:
        meta = ProjectValidator().validate(tmp_c_project)
        file_names = {f.name for f in meta.source_files}
        assert "output.o" not in file_names

    def test_raises_on_nonexistent_path(self, tmp_path: Path) -> None:
        with pytest.raises(ValidationError, match="does not exist"):
            ProjectValidator().validate(tmp_path / "no_such_dir")

    def test_raises_on_empty_project(self, tmp_path: Path) -> None:
        empty = tmp_path / "empty"
        empty.mkdir()
        with pytest.raises(ValidationError, match="No C/C\\+\\+"):
            ProjectValidator().validate(empty)

    def test_detects_cpp_language(self, tmp_path: Path) -> None:
        proj = tmp_path / "cpp_proj"
        proj.mkdir()
        (proj / "main.cpp").write_text("int main() {}\n")
        meta = ProjectValidator().validate(proj)
        assert meta.language == "C++"

    def test_detects_mixed_language(self, tmp_path: Path) -> None:
        proj = tmp_path / "mixed_proj"
        proj.mkdir()
        (proj / "main.c").write_text("int main() {}\n")
        (proj / "ext.cpp").write_text("void ext() {}\n")
        meta = ProjectValidator().validate(proj)
        assert meta.language == "Mixed"


# ── ZIPExtractor tests ─────────────────────────────────────

class TestZIPExtractor:

    def test_extracts_zip(self, tmp_zip: Path, tmp_path: Path) -> None:
        dest = ZIPExtractor().extract(tmp_zip, tmp_path / "workspace")
        assert dest.exists()
        assert dest.is_dir()

    def test_raises_on_non_zip(self, tmp_path: Path) -> None:
        fake = tmp_path / "fake.zip"
        fake.write_bytes(b"not a zip")
        with pytest.raises(ExtractionError, match="not a valid ZIP"):
            ZIPExtractor().extract(fake, tmp_path / "ws")

    def test_raises_on_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(ExtractionError, match="not found"):
            ZIPExtractor().extract(tmp_path / "missing.zip", tmp_path / "ws")


# ── Normalizer tests ───────────────────────────────────────

class TestNormalizer:

    def test_normalizes_crlf(self, tmp_path: Path) -> None:
        f = tmp_path / "file.c"
        f.write_bytes(b"int main() {\r\n  return 0;\r\n}\r\n")
        Normalizer().normalize_project(tmp_path, [f])
        assert b"\r\n" not in f.read_bytes()

    def test_strips_bom(self, tmp_path: Path) -> None:
        f = tmp_path / "file.c"
        f.write_bytes(b"\xef\xbb\xbfint main() {}\n")
        Normalizer().normalize_project(tmp_path, [f])
        content = f.read_text()
        assert not content.startswith("\ufeff")

    def test_no_op_for_clean_file(self, tmp_path: Path) -> None:
        clean = "int main() {\n  return 0;\n}\n"
        f = tmp_path / "file.c"
        f.write_text(clean)
        n = Normalizer().normalize_project(tmp_path, [f])
        assert n == 0
