# ============================================================
# Git Repository Provider — Hardened Isolated Git Ingestion
# ============================================================

from __future__ import annotations

import asyncio
import os
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger

from backend.app.core.exceptions import StorageError
from backend.app.services.vcs.base import CommitInfo, RepositoryProvider


class GitProvider(RepositoryProvider):
    """Hardened local/generic Git repository provider."""

    TIMEOUT_SECONDS = 60

    def _prepare_env(self, token: str | None = None) -> dict[str, str]:
        """Set up environment variables disabling hooks, prompts, and credentials leakage."""
        env = os.environ.copy()
        env["GIT_TERMINAL_PROMPT"] = "0"
        env["GIT_ASKPASS"] = "echo"
        env["GIT_CONFIG_GLOBAL"] = "/dev/null"
        env["GIT_CONFIG_SYSTEM"] = "/dev/null"
        return env

    def _format_url_with_auth(self, repo_url: str, token: str | None = None) -> str:
        """Embed token safely for authentication if provided."""
        if not token:
            return repo_url
        clean = repo_url.strip()
        if clean.startswith("https://"):
            return f"https://x-access-token:{token}@{clean[8:]}"
        elif clean.startswith("http://"):
            return f"http://x-access-token:{token}@{clean[7:]}"
        return clean

    async def _run_git(
        self, args: list[str], cwd: Path | None = None, token: str | None = None
    ) -> tuple[str, str]:
        """Execute git command with security flags and timeout."""
        cmd = ["git", "-c", "core.hooksPath=/dev/null", "-c", "advice.detachedHead=false"] + args
        env = self._prepare_env(token)

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(cwd) if cwd else None,
            env=env,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=self.TIMEOUT_SECONDS
            )
        except asyncio.TimeoutError:
            proc.kill()
            raise StorageError(f"Git operation timed out after {self.TIMEOUT_SECONDS}s")

        if proc.returncode != 0:
            err_msg = stderr.decode(errors="replace").strip()
            # Redact any possible token in error message
            if token and token in err_msg:
                err_msg = err_msg.replace(token, "[REDACTED]")
            raise StorageError(f"Git command failed: {err_msg}")

        return stdout.decode(errors="replace").strip(), stderr.decode(errors="replace").strip()

    async def validate_connection(self, repo_url: str, token: str | None = None) -> bool:
        """Check if remote repository is reachable."""
        try:
            auth_url = self._format_url_with_auth(repo_url, token)
            await self._run_git(["ls-remote", "--exit-code", "-h", auth_url], token=token)
            return True
        except Exception as exc:
            logger.warning("Git connection validation failed for repository: {err}", err=str(exc))
            return False

    async def list_branches(self, repo_url: str, token: str | None = None) -> list[str]:
        """List branches from git ls-remote."""
        auth_url = self._format_url_with_auth(repo_url, token)
        stdout, _ = await self._run_git(["ls-remote", "--heads", auth_url], token=token)
        branches = []
        for line in stdout.splitlines():
            parts = line.strip().split()
            if len(parts) >= 2 and parts[1].startswith("refs/heads/"):
                branches.append(parts[1].replace("refs/heads/", ""))
        return sorted(branches) if branches else ["main"]

    async def get_default_branch(self, repo_url: str, token: str | None = None) -> str:
        """Discover default branch."""
        branches = await self.list_branches(repo_url, token)
        if "main" in branches:
            return "main"
        if "master" in branches:
            return "master"
        return branches[0] if branches else "main"

    async def fetch_latest_commit(
        self, repo_url: str, branch: str, token: str | None = None
    ) -> CommitInfo:
        """Discover latest commit sha using ls-remote without full clone."""
        auth_url = self._format_url_with_auth(repo_url, token)
        stdout, _ = await self._run_git(["ls-remote", "--heads", auth_url, branch], token=token)
        sha = "0000000000000000000000000000000000000000"
        for line in stdout.splitlines():
            parts = line.strip().split()
            if len(parts) >= 2:
                sha = parts[0]
                break

        return {
            "commit_sha": sha,
            "short_sha": sha[:8],
            "author_name": "Git Author",
            "author_email": "author@git.local",
            "message": f"Synchronized from branch {branch}",
            "committed_at": datetime.now(timezone.utc),
        }

    async def fetch_and_package_source(
        self,
        repo_url: str,
        branch: str,
        target_zip_path: Path,
        commit_sha: str | None = None,
        token: str | None = None,
    ) -> CommitInfo:
        """Clone shallow, checkout, extract metadata, and zip working tree."""
        temp_dir = Path(tempfile.mkdtemp(prefix="git_ingest_"))
        try:
            auth_url = self._format_url_with_auth(repo_url, token)
            clone_dir = temp_dir / "repo"

            # 1. Shallow clone
            await self._run_git(
                [
                    "clone",
                    "--depth", "1",
                    "--branch", branch,
                    "--single-branch",
                    "--config", "core.hooksPath=/dev/null",
                    auth_url,
                    str(clone_dir),
                ],
                token=token,
            )

            # 2. Extract commit info using git log
            log_stdout, _ = await self._run_git(
                ["log", "-1", "--format=%H%x00%an%x00%ae%x00%at%x00%s"],
                cwd=clone_dir,
                token=token,
            )
            parts = log_stdout.split("\x00")
            actual_sha = parts[0].strip() if len(parts) > 0 else "unknown"
            author_name = parts[1].strip() if len(parts) > 1 else "Unknown"
            author_email = parts[2].strip() if len(parts) > 2 else "unknown@domain.local"
            timestamp = int(parts[3].strip()) if len(parts) > 3 and parts[3].strip().isdigit() else int(datetime.now(timezone.utc).timestamp())
            commit_msg = parts[4].strip() if len(parts) > 4 else "VCS Import"

            commit_info: CommitInfo = {
                "commit_sha": actual_sha,
                "short_sha": actual_sha[:8],
                "author_name": author_name,
                "author_email": author_email,
                "message": commit_msg,
                "committed_at": datetime.fromtimestamp(timestamp, tz=timezone.utc),
            }

            # 3. Package working tree into ZIP, strictly omitting .git
            target_zip_path.parent.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(target_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for root, dirs, files in os.walk(clone_dir):
                    if ".git" in dirs:
                        dirs.remove(".git")
                    for file in files:
                        full_path = Path(root) / file
                        arcname = full_path.relative_to(clone_dir).as_posix()
                        zf.write(full_path, arcname)

            return commit_info
        finally:
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
