# ============================================================
# Preprocessing Service (Phase 3 Production Pipeline)
# ============================================================

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import shutil
import tempfile
import uuid
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from loguru import logger
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import get_settings
from backend.app.core.exceptions import StorageError
from backend.app.models.source_snapshot import Function, SourceFile, SourceSnapshot
from backend.app.services.code_parser import (
    NORMALIZATION_VERSION,
    TOKENIZER_VERSION,
    classify_file,
    detect_duplicate_functions,
    detect_file_language,
    extract_functions,
    is_binary_content,
    normalize_identifiers,
    sanitize_relative_path,
    tokenize_code,
)
from backend.app.storage.service import StorageService
from backend.app.utils.zip_utils import safe_extract_zip


class SnapshotProcessingResult:
    def __init__(
        self,
        snapshot_id: uuid.UUID,
        status: str,
        file_count: int,
        total_bytes: int,
        detected_languages: dict[str, int],
        function_count: int,
        duplicate_count: int,
        manifest_uri: str,
        content_hash: str,
        error_message: str | None = None,
    ):
        self.snapshot_id = snapshot_id
        self.status = status
        self.file_count = file_count
        self.total_bytes = total_bytes
        self.detected_languages = detected_languages
        self.function_count = function_count
        self.duplicate_count = duplicate_count
        self.manifest_uri = manifest_uri
        self.content_hash = content_hash
        self.error_message = error_message


class PreprocessingService:
    """Prepares and processes immutable source code snapshots for security analysis."""

    PREPROCESSING_VERSION = "v1.0.0"

    def __init__(self, storage_service: StorageService | None = None):
        self.storage = storage_service or StorageService()
        self.settings = get_settings()

    async def process_snapshot(
        self,
        db: AsyncSession,
        snapshot_id: uuid.UUID,
        org_id: uuid.UUID,
        project_id: uuid.UUID,
    ) -> SnapshotProcessingResult:
        """Execute the complete validation, extraction, tokenization, and normalization pipeline.

        Runs inside an isolated worker workspace.
        Original and derived artifacts are persisted directly to S3/MinIO.
        """
        stmt = select(SourceSnapshot).where(SourceSnapshot.id == snapshot_id)
        res = await db.execute(stmt)
        snapshot = res.scalar_one_or_none()
        if not snapshot:
            raise ValueError(f"SourceSnapshot {snapshot_id} not found")

        # Mark snapshot as processing and clear existing files/functions for idempotent re-runs
        snapshot.status = "processing"
        await db.execute(delete(SourceFile).where(SourceFile.source_snapshot_id == snapshot_id))
        await db.commit()

        temp_dir = Path(tempfile.mkdtemp(prefix=f"snapshot_{snapshot_id}_"))
        try:
            # 1. Download raw artifact from S3 into temporary workspace
            raw_archive_bytes = await self.storage.read_file(snapshot.artifact_uri)
            archive_path = temp_dir / "raw_source.zip"
            archive_path.write_bytes(raw_archive_bytes)

            extract_dir = temp_dir / "extracted"
            extract_dir.mkdir(parents=True, exist_ok=True)

            # 2. Hardened extraction with zip-slip containment checks
            if snapshot.source_type in ("upload_zip", "git", "github") or zipfile.is_zipfile(archive_path):
                safe_extract_zip(archive_path, extract_dir)
            else:
                # Direct single-file or tarball
                shutil.copy2(archive_path, extract_dir / "source_file")

            # 3. Enumerate all extracted files
            discovered_files: list[Path] = []
            for root, _, files in os.walk(extract_dir):
                for f in files:
                    full_path = Path(root) / f
                    discovered_files.append(full_path)

            source_file_models: list[SourceFile] = []
            all_extracted_functions: list[dict] = []
            file_function_map: dict[str, list[dict]] = {}
            language_counter: Counter = Counter()
            total_bytes = 0

            # 4. Process each file
            for full_file_path in discovered_files:
                raw_rel = full_file_path.relative_to(extract_dir).as_posix()
                try:
                    rel_path = sanitize_relative_path(raw_rel)
                except ValueError as err:
                    logger.warning("Skipping unsafe path in snapshot {id}: {p} ({err})", id=snapshot_id, p=raw_rel, err=err)
                    continue

                content_bytes = full_file_path.read_bytes()
                size_bytes = len(content_bytes)
                total_bytes += size_bytes
                content_hash = hashlib.sha256(content_bytes).hexdigest()
                path_hash = hashlib.sha256(rel_path.encode("utf-8")).hexdigest()

                is_bin = is_binary_content(content_bytes)
                val_status, is_excluded = classify_file(rel_path, size_bytes, is_bin)

                text_content = ""
                encoding = "utf-8"
                if not is_bin:
                    try:
                        text_content = content_bytes.decode("utf-8")
                    except UnicodeDecodeError:
                        try:
                            text_content = content_bytes.decode("latin-1")
                            encoding = "latin-1"
                        except Exception:
                            is_bin = True
                            val_status = "unsupported"

                lang = detect_file_language(rel_path, sample_content=text_content[:2048] if text_content else None)
                if lang:
                    language_counter[lang] += 1

                line_count = len(text_content.splitlines()) if text_content else 0

                # Store original artifact in S3/MinIO
                orig_key = StorageService.snapshot_file_key(org_id, project_id, snapshot_id, rel_path, kind="original")
                await self.storage.save_object(content_bytes, orig_key)

                norm_key = None
                token_key = None

                # Perform analysis parsing for valid source files
                if val_status == "valid" and not is_excluded and text_content and lang:
                    try:
                        # Identifier normalization
                        norm_code, _ = normalize_identifiers(text_content, language=lang)
                        norm_key = StorageService.snapshot_file_key(org_id, project_id, snapshot_id, rel_path, kind="normalized")
                        await self.storage.save_object(norm_code.encode("utf-8"), norm_key)

                        # Tokenization
                        tokens_res = tokenize_code(text_content, language=lang)
                        token_key = StorageService.snapshot_file_key(org_id, project_id, snapshot_id, rel_path, kind="tokens")
                        await self.storage.save_object(
                            json.dumps(tokens_res.to_dict()).encode("utf-8"),
                            token_key,
                        )

                        # Function extraction
                        funcs = extract_functions(text_content, lang, str(snapshot_id), rel_path)
                        if funcs:
                            file_function_map[rel_path] = funcs
                            all_extracted_functions.extend(funcs)
                    except Exception as parse_exc:
                        logger.warning("Parsing warning on {p}: {err}", p=rel_path, err=parse_exc)

                sf_model = SourceFile(
                    id=uuid.uuid4(),
                    source_snapshot_id=snapshot_id,
                    relative_path=rel_path,
                    path_hash=path_hash,
                    language=lang,
                    size_bytes=size_bytes,
                    content_hash=content_hash,
                    original_artifact_uri=orig_key,
                    normalized_artifact_uri=norm_key,
                    token_artifact_uri=token_key,
                    line_count=line_count,
                    encoding=encoding,
                    is_binary=is_bin,
                    is_generated=False,
                    validation_status=val_status,
                    preprocessing_status="processed",
                )
                source_file_models.append(sf_model)

            # 5. Detect duplicate functions across snapshot
            duplicate_map = detect_duplicate_functions(all_extracted_functions)

            # 6. Build Function database models linked to SourceFile
            function_models: list[Function] = []
            file_model_by_path = {sf.relative_path: sf for sf in source_file_models}

            for rel_path, funcs in file_function_map.items():
                sf = file_model_by_path.get(rel_path)
                if not sf:
                    continue
                for f_data in funcs:
                    fid = f_data["function_id"]
                    dup_group = duplicate_map.get(fid)
                    fn_model = Function(
                        id=uuid.uuid4(),
                        source_file_id=sf.id,
                        function_id=fid,
                        qualified_name=f_data["qualified_name"],
                        name=f_data["name"],
                        language=f_data["language"],
                        start_line=f_data["start_line"],
                        end_line=f_data["end_line"],
                        start_byte=f_data["start_byte"],
                        end_byte=f_data["end_byte"],
                        signature=f_data["signature"],
                        original_content_hash=f_data["original_content_hash"],
                        normalized_content_hash=f_data["normalized_content_hash"],
                        token_count=f_data["token_count"],
                        duplicate_group_id=dup_group,
                        extraction_status="extracted",
                    )
                    function_models.append(fn_model)

            # 7. Generate Snapshot Manifest
            manifest_data = {
                "snapshot_id": str(snapshot_id),
                "project_id": str(project_id),
                "organization_id": str(org_id),
                "preprocessing_version": self.PREPROCESSING_VERSION,
                "tokenizer_version": TOKENIZER_VERSION,
                "normalization_version": NORMALIZATION_VERSION,
                "file_count": len(source_file_models),
                "function_count": len(function_models),
                "duplicate_count": len(duplicate_map),
                "total_bytes": total_bytes,
                "detected_languages": dict(language_counter),
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "files": [
                    {
                        "path": sf.relative_path,
                        "hash": sf.content_hash,
                        "size": sf.size_bytes,
                        "language": sf.language,
                        "status": sf.validation_status,
                    }
                    for sf in source_file_models
                ],
            }
            manifest_json_bytes = json.dumps(manifest_data, indent=2).encode("utf-8")
            manifest_hash = hashlib.sha256(manifest_json_bytes).hexdigest()
            manifest_key = StorageService.snapshot_manifest_key(org_id, project_id, snapshot_id)
            await self.storage.save_object(manifest_json_bytes, manifest_key)

            # 8. Persist metadata to PostgreSQL atomically
            db.add_all(source_file_models)
            db.add_all(function_models)

            snapshot.status = "ready"
            snapshot.file_count = len(source_file_models)
            snapshot.total_bytes = total_bytes
            snapshot.detected_languages = dict(language_counter)
            snapshot.content_hash = manifest_hash
            snapshot.manifest_uri = manifest_key
            snapshot.completed_at = datetime.now(timezone.utc)
            snapshot.failure_reason = None
            await db.commit()

            logger.info(
                "Successfully processed snapshot {id}: {files} files, {funcs} functions, {dups} duplicates",
                id=snapshot_id,
                files=len(source_file_models),
                funcs=len(function_models),
                dups=len(duplicate_map),
            )

            return SnapshotProcessingResult(
                snapshot_id=snapshot_id,
                status="ready",
                file_count=len(source_file_models),
                total_bytes=total_bytes,
                detected_languages=dict(language_counter),
                function_count=len(function_models),
                duplicate_count=len(duplicate_map),
                manifest_uri=manifest_key,
                content_hash=manifest_hash,
            )

        except Exception as exc:
            logger.exception("Failed to process snapshot {id}: {err}", id=snapshot_id, err=str(exc))
            snapshot.status = "failed"
            snapshot.failure_reason = str(exc)
            await db.commit()
            return SnapshotProcessingResult(
                snapshot_id=snapshot_id,
                status="failed",
                file_count=0,
                total_bytes=0,
                detected_languages={},
                function_count=0,
                duplicate_count=0,
                manifest_uri="",
                content_hash="",
                error_message=str(exc),
            )
        finally:
            # Clean up temporary isolated workspace
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
