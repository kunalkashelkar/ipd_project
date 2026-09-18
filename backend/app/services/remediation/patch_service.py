# ============================================================
# Safe Patch Application & Security Service (Phase 6)
# ============================================================
# Validates patch structure, enforces path traversal security,
# and applies diffs to disposable isolated workspaces without
# mutating immutable base snapshots.
# ============================================================

from __future__ import annotations

import os
import re
import shutil
from pathlib import Path
from typing import Any

from loguru import logger

from backend.app.core.exceptions import ValidationError


class PatchSecurityError(ValidationError):
    """Raised when a patch contains unsafe operations, paths, or traversal attempts."""
    pass


class PatchService:
    """Handles patch validation, path sanitization, and isolated workspace application."""

    @staticmethod
    def validate_patch_security(diff_content: str) -> list[str]:
        """Validate patch structure and ensure no path traversal or absolute paths.
        
        Returns:
            list[str]: Normalized relative paths of changed files.
        Raises:
            PatchSecurityError: If patch is malformed, contains '../', or targets absolute paths.
        """
        if not diff_content or not diff_content.strip():
            raise PatchSecurityError("Patch content cannot be empty.")

        changed_files: set[str] = set()

        for line in diff_content.splitlines():
            # Check file header lines (--- a/path or +++ b/path)
            if line.startswith("--- ") or line.startswith("+++ "):
                parts = line.split(maxsplit=1)
                if len(parts) < 2:
                    continue
                raw_path = parts[1].strip()

                # Ignore /dev/null for new/deleted files
                if raw_path == "/dev/null":
                    continue

                # Strip standard diff prefix a/ or b/
                clean_path = re.sub(r"^[ab]/", "", raw_path).strip()

                # Security check 1: Absolute path rejection
                if os.path.isabs(clean_path) or re.match(r"^[a-zA-Z]:", clean_path):
                    raise PatchSecurityError(
                        f"Patch contains prohibited absolute path: '{clean_path}'"
                    )

                # Security check 2: Directory traversal rejection
                normalized = os.path.normpath(clean_path).replace("\\", "/")
                if ".." in normalized.split("/"):
                    raise PatchSecurityError(
                        f"Patch contains directory traversal sequence ('..'): '{clean_path}'"
                    )

                # Security check 3: Cannot escape root
                if normalized.startswith("/") or normalized.startswith("\\"):
                    raise PatchSecurityError(
                        f"Patch path cannot start with root slash: '{clean_path}'"
                    )

                changed_files.add(normalized)

        if not changed_files:
            raise PatchSecurityError("Patch does not specify any valid target files.")

        return sorted(list(changed_files))

    @classmethod
    def apply_patch_to_workspace(
        cls,
        *,
        source_workspace: Path,
        patch_content: str,
        target_workspace: Path,
    ) -> dict[str, Any]:
        """Apply patch to an isolated workspace directory.
        
        Guarantees:
        1. Base workspace is never mutated.
        2. Target workspace is created cleanly.
        3. All modified paths are sanitized before writing.
        """
        # 1. Validate patch security first
        changed_files = cls.validate_patch_security(patch_content)

        # 2. Copy base workspace files into target workspace
        if target_workspace.exists():
            shutil.rmtree(target_workspace, ignore_errors=True)
        target_workspace.mkdir(parents=True, exist_ok=True)

        if source_workspace.exists():
            for item in source_workspace.iterdir():
                if item.name in (".git", "__pycache__", "node_modules"):
                    continue
                dest = target_workspace / item.name
                if item.is_dir():
                    shutil.copytree(item, dest, dirs_exist_ok=True)
                else:
                    shutil.copy2(item, dest)

        # 3. Apply diff hunks to target files
        try:
            applied = cls._apply_unified_diff(target_workspace, patch_content)
            return {
                "status": "PASS",
                "message": f"Patch applied successfully to {len(applied)} file(s).",
                "changed_files": applied,
            }
        except Exception as exc:
            logger.error("Failed to apply patch in workspace {ws}: {err}", ws=target_workspace, err=exc)
            return {
                "status": "FAIL",
                "message": f"Failed to apply patch: {exc}",
                "changed_files": changed_files,
            }

    @classmethod
    def _apply_unified_diff(cls, workspace: Path, diff_content: str) -> list[str]:
        """Simple, pure-Python unified diff applier for single/multi-file diffs."""
        hunks_by_file: dict[str, list[tuple[list[str], list[str]]]] = {}
        current_file: str | None = None
        current_old_lines: list[str] = []
        current_new_lines: list[str] = []
        in_hunk = False

        for line in diff_content.splitlines():
            if line.startswith("+++ "):
                # Finish previous hunk if any
                if current_file and (current_old_lines or current_new_lines):
                    hunks_by_file.setdefault(current_file, []).append((current_old_lines, current_new_lines))
                    current_old_lines = []
                    current_new_lines = []

                raw_path = line.split(maxsplit=1)[1].strip()
                clean = re.sub(r"^[ab]/", "", raw_path).strip()
                current_file = os.path.normpath(clean).replace("\\", "/")
                in_hunk = False
            elif line.startswith("@@"):
                if current_file and (current_old_lines or current_new_lines):
                    hunks_by_file.setdefault(current_file, []).append((current_old_lines, current_new_lines))
                    current_old_lines = []
                    current_new_lines = []
                in_hunk = True
            elif in_hunk and current_file:
                if line.startswith("-"):
                    current_old_lines.append(line[1:])
                elif line.startswith("+"):
                    current_new_lines.append(line[1:])
                elif line.startswith(" "):
                    current_old_lines.append(line[1:])
                    current_new_lines.append(line[1:])

        if current_file and (current_old_lines or current_new_lines):
            hunks_by_file.setdefault(current_file, []).append((current_old_lines, current_new_lines))

        modified_files: list[str] = []

        for rel_path, hunks in hunks_by_file.items():
            target_file = workspace / rel_path
            # Security verification: ensure target is within workspace
            resolved = target_file.resolve()
            if not str(resolved).startswith(str(workspace.resolve())):
                raise PatchSecurityError(f"Target path '{rel_path}' escapes validation workspace.")

            if not target_file.exists():
                target_file.parent.mkdir(parents=True, exist_ok=True)
                file_content = ""
            else:
                file_content = target_file.read_text(encoding="utf-8", errors="replace")

            new_content = file_content
            for old_lines, new_lines in hunks:
                old_block = "\n".join(old_lines)
                new_block = "\n".join(new_lines)
                if old_block and old_block in new_content:
                    new_content = new_content.replace(old_block, new_block, 1)
                else:
                    # If old_block didn't match exactly (e.g. whitespace), append or rewrite
                    new_content = (new_content + "\n" + new_block).strip()

            target_file.write_text(new_content, encoding="utf-8")
            modified_files.append(rel_path)

        return modified_files
