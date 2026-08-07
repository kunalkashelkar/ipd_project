# ============================================================
# Preprocessing Service
# ============================================================
# Bridge between upload and AI — prepares code for inference.
# Does NOT depend on AI models.
# ============================================================

from __future__ import annotations

import json
import uuid
from pathlib import Path

from pydantic import BaseModel

from backend.app.core.config import get_settings
from backend.app.core.logging import logger
from backend.app.utils.language_detector import detect_language
from backend.app.utils.zip_utils import safe_extract_zip


class PreprocessingResult(BaseModel):
    """Result of preprocessing an upload."""

    upload_id: str
    status: str = "processed"
    language: str = "unknown"
    file_count: int = 0
    function_count: int = 0
    duplicate_count: int = 0
    token_count: int = 0
    manifest_path: str = ""
    files: list[dict] = []


class PreprocessingService:
    """Prepares uploaded code for AI inference."""

    def __init__(self):
        self.settings = get_settings()

    def process_upload(self, upload_stored_path: str, upload_id: str) -> PreprocessingResult:
        """Process an uploaded file/archive.

        Steps:
        1. Extract if ZIP
        2. Detect language
        3. Enumerate source files
        4. Basic function extraction (stub)
        5. Generate metadata
        """
        stored_path = Path(upload_stored_path)
        upload_dir = stored_path.parent
        extracted_dir = upload_dir / "extracted"

        # Step 1: Extract if ZIP
        if stored_path.suffix.lower() == ".zip":
            extracted_dir.mkdir(parents=True, exist_ok=True)
            safe_extract_zip(stored_path, extracted_dir)
            source_dir = extracted_dir
        else:
            source_dir = upload_dir

        # Step 2: Enumerate source files
        source_files = self._enumerate_source_files(source_dir)

        # Step 3: Detect language
        language = self._detect_primary_language(source_files)

        # Step 4: Basic function extraction (stub — returns file-level entries)
        functions = self._extract_functions_stub(source_files, source_dir)

        # Step 5: Estimate token count
        total_tokens = sum(f.get("token_count", 0) for f in functions)

        # Step 6: Generate manifest
        manifest = {
            "upload_id": upload_id,
            "language": language,
            "file_count": len(source_files),
            "function_count": len(functions),
            "token_count": total_tokens,
            "files": [str(f.relative_to(source_dir)) for f in source_files],
        }
        manifest_path = upload_dir / "processed_manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2))

        # Save functions list
        functions_path = upload_dir / "functions.json"
        functions_path.write_text(json.dumps(functions, indent=2))

        logger.info(
            "Preprocessed upload {id}: {files} files, {funcs} functions, {lang} detected",
            id=upload_id,
            files=len(source_files),
            funcs=len(functions),
            lang=language,
        )

        return PreprocessingResult(
            upload_id=upload_id,
            status="processed",
            language=language,
            file_count=len(source_files),
            function_count=len(functions),
            token_count=total_tokens,
            manifest_path=str(manifest_path),
            files=functions,
        )

    def _enumerate_source_files(self, source_dir: Path) -> list[Path]:
        """Find all source code files in a directory."""
        extensions = {".java", ".py", ".js", ".ts", ".c", ".cpp", ".h", ".hpp", ".cs", ".go", ".rs"}
        files = []
        for f in source_dir.rglob("*"):
            if f.is_file() and f.suffix.lower() in extensions:
                files.append(f)
        return files

    def _detect_primary_language(self, files: list[Path]) -> str:
        """Detect the primary language from file extensions."""
        if not files:
            return "unknown"
        from collections import Counter

        langs = Counter(detect_language(f.suffix) for f in files)
        return langs.most_common(1)[0][0]

    def _extract_functions_stub(self, files: list[Path], source_dir: Path) -> list[dict]:
        """Stub function extraction — returns one entry per file.

        TODO: Replace with tree-sitter based parsing for real function extraction.
        """
        functions = []
        for f in files:
            try:
                content = f.read_text(errors="replace")
                token_estimate = len(content.split())
                functions.append({
                    "file": str(f.relative_to(source_dir)),
                    "function": f.stem,
                    "start_line": 1,
                    "end_line": content.count("\n") + 1,
                    "language": detect_language(f.suffix),
                    "token_count": token_estimate,
                    "code": content[:5000],  # Limit for mock purposes
                })
            except Exception:
                continue
        return functions
