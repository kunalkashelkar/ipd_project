# ============================================================
# VCS Repository Provider Abstract Interface (Phase 3)
# ============================================================

from __future__ import annotations

import abc
from datetime import datetime
from pathlib import Path
from typing import TypedDict


class CommitInfo(TypedDict):
    commit_sha: str
    short_sha: str
    author_name: str
    author_email: str
    message: str
    committed_at: datetime


class RepositoryProvider(abc.ABC):
    """Abstract interface decoupling VCS providers (Local Git, GitHub, GitLab) from business logic."""

    @abc.abstractmethod
    async def validate_connection(self, repo_url: str, token: str | None = None) -> bool:
        """Validate whether the repository URL is reachable and accessible."""
        pass

    @abc.abstractmethod
    async def list_branches(self, repo_url: str, token: str | None = None) -> list[str]:
        """List all available remote branches."""
        pass

    @abc.abstractmethod
    async def get_default_branch(self, repo_url: str, token: str | None = None) -> str:
        """Identify the default branch (e.g. 'main', 'master')."""
        pass

    @abc.abstractmethod
    async def fetch_latest_commit(
        self, repo_url: str, branch: str, token: str | None = None
    ) -> CommitInfo:
        """Fetch the latest commit metadata on the specified branch."""
        pass

    @abc.abstractmethod
    async def fetch_and_package_source(
        self,
        repo_url: str,
        branch: str,
        target_zip_path: Path,
        commit_sha: str | None = None,
        token: str | None = None,
    ) -> CommitInfo:
        """Fetch source code and package into an isolated ZIP archive."""
        pass
