# ============================================================
# GitHub Repository Provider — Real GitHub API / VCS Ingestion
# ============================================================

from __future__ import annotations

import io
import os
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import httpx
from loguru import logger

from backend.app.core.exceptions import StorageError
from backend.app.services.vcs.base import CommitInfo, RepositoryProvider
from backend.app.services.vcs.git_provider import GitProvider


class GitHubProvider(RepositoryProvider):
    """GitHub repository provider supporting public and token-authenticated repositories."""

    def __init__(self):
        self.git_provider = GitProvider()

    def _normalize_repo_coords(self, repo_url: str) -> tuple[str, str]:
        """Parse (owner, repo) from URL or slug (e.g. 'owner/repo', 'https://github.com/owner/repo', 'git@github.com:owner/repo.git')."""
        clean = repo_url.strip().rstrip("/")
        if clean.endswith(".git"):
            clean = clean[:-4]

        # Handle SSH format git@github.com:owner/repo
        if "github.com:" in clean:
            clean = clean.split("github.com:")[-1]
        elif "github.com/" in clean:
            clean = clean.split("github.com/")[-1]

        clean = clean.strip("/")
        parts = clean.split("/")
        if len(parts) >= 2 and parts[-2] and parts[-1]:
            owner = parts[-2].split("@")[-1]
            repo = parts[-1]
            return owner, repo

        raise ValueError(
            f"Invalid GitHub repository identifier: '{repo_url}'. Expected format: 'owner/repo' or 'https://github.com/owner/repo'"
        )

    def _get_headers(self, token: str | None = None) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "VulnScan-Security-Platform/1.0",
        }
        if token and token.strip():
            headers["Authorization"] = f"Bearer {token.strip()}"
        return headers

    async def validate_connection(self, repo_url: str, token: str | None = None) -> bool:
        """Validate repository existence and access via GitHub API or git ls-remote."""
        owner, repo = self._normalize_repo_coords(repo_url)
        api_url = f"https://api.github.com/repos/{owner}/{repo}"
        full_git_url = f"https://github.com/{owner}/{repo}.git"

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(api_url, headers=self._get_headers(token))
                if resp.status_code == 200:
                    return True

                if resp.status_code == 401:
                    raise ValueError(
                        "GitHub authentication failed: Bad credentials. Please verify your Personal Access Token."
                    )

                if resp.status_code == 404:
                    # Could be private without token or genuinely not found; try git ls-remote fallback
                    try:
                        if await self.git_provider.validate_connection(full_git_url, token):
                            return True
                    except Exception:
                        pass

                    if token:
                        raise ValueError(
                            f"Repository '{owner}/{repo}' not found or the provided Personal Access Token lacks read permissions."
                        )
                    else:
                        raise ValueError(
                            f"Repository '{owner}/{repo}' not found or is private. If this repository is private, please provide a Personal Access Token."
                        )

                if resp.status_code == 403:
                    # Check for rate limiting
                    resp_json = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
                    message = resp_json.get("message", "")
                    if "rate limit" in message.lower():
                        # Try git ls-remote fallback
                        if await self.git_provider.validate_connection(full_git_url, token):
                            return True
                        raise ValueError(
                            "GitHub API rate limit reached. Please provide a Personal Access Token with read access or try again later."
                        )
                    raise ValueError(f"GitHub access forbidden: {message or 'Forbidden'}")

                raise ValueError(f"GitHub returned HTTP {resp.status_code} while validating repository.")

        except (httpx.ConnectError, httpx.TimeoutException) as net_err:
            # Try git ls-remote fallback on network timeout
            try:
                if await self.git_provider.validate_connection(full_git_url, token):
                    return True
            except Exception:
                pass
            raise ValueError(f"Could not connect to GitHub repository: {net_err}")

    async def list_branches(self, repo_url: str, token: str | None = None) -> list[str]:
        """Fetch remote branches from GitHub."""
        try:
            owner, repo = self._normalize_repo_coords(repo_url)
            api_url = f"https://api.github.com/repos/{owner}/{repo}/branches"
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(api_url, headers=self._get_headers(token), params={"per_page": 100})
                if resp.status_code == 200:
                    branches = [b["name"] for b in resp.json()]
                    if branches:
                        return branches
        except Exception:
            pass

        # Fallback to git provider
        owner, repo = self._normalize_repo_coords(repo_url)
        full_git_url = f"https://github.com/{owner}/{repo}.git"
        return await self.git_provider.list_branches(full_git_url, token)

    async def get_default_branch(self, repo_url: str, token: str | None = None) -> str:
        """Get the repository's default branch."""
        try:
            owner, repo = self._normalize_repo_coords(repo_url)
            api_url = f"https://api.github.com/repos/{owner}/{repo}"
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(api_url, headers=self._get_headers(token))
                if resp.status_code == 200:
                    def_branch = resp.json().get("default_branch")
                    if def_branch:
                        return def_branch
        except Exception:
            pass

        # Fallback: check available branches from remote
        try:
            branches = await self.list_branches(repo_url, token)
            if "main" in branches:
                return "main"
            if "master" in branches:
                return "master"
            if branches:
                return branches[0]
        except Exception:
            pass

        return "main"

    async def fetch_latest_commit(
        self, repo_url: str, branch: str, token: str | None = None
    ) -> CommitInfo:
        """Fetch commit details on the given branch."""
        try:
            owner, repo = self._normalize_repo_coords(repo_url)
            api_url = f"https://api.github.com/repos/{owner}/{repo}/commits/{branch}"
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(api_url, headers=self._get_headers(token))
                if resp.status_code == 200:
                    data = resp.json()
                    sha = data["sha"]
                    commit_obj = data.get("commit", {})
                    author_obj = commit_obj.get("author", {})
                    date_str = author_obj.get("date")
                    committed_at = (
                        datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                        if date_str
                        else datetime.now(timezone.utc)
                    )
                    return {
                        "commit_sha": sha,
                        "short_sha": sha[:8],
                        "author_name": author_obj.get("name", "GitHub Committer"),
                        "author_email": author_obj.get("email", "committer@github.com"),
                        "message": commit_obj.get("message", "Sync from GitHub"),
                        "committed_at": committed_at,
                    }
        except Exception:
            pass

        # Fallback to git provider
        owner, repo = self._normalize_repo_coords(repo_url)
        full_git_url = f"https://github.com/{owner}/{repo}.git"
        return await self.git_provider.fetch_latest_commit(full_git_url, branch, token)

    async def fetch_and_package_source(
        self,
        repo_url: str,
        branch: str,
        target_zip_path: Path,
        commit_sha: str | None = None,
        token: str | None = None,
    ) -> CommitInfo:
        """Download source archive from GitHub API or shallow clone via Git."""
        owner, repo = self._normalize_repo_coords(repo_url)
        commit_info = await self.fetch_latest_commit(repo_url, branch, token)
        ref = commit_sha or commit_info["commit_sha"] or branch

        # Try downloading tarball/zipball directly from GitHub API
        try:
            zipball_url = f"https://api.github.com/repos/{owner}/{repo}/zipball/{ref}"
            async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
                resp = await client.get(zipball_url, headers=self._get_headers(token))
                if resp.status_code == 200 and len(resp.content) > 0:
                    # Strip the top-level directory wrapper that GitHub injects into zipballs
                    temp_extract = Path(tempfile.mkdtemp(prefix="gh_strip_"))
                    try:
                        raw_zip = io.BytesIO(resp.content)
                        with zipfile.ZipFile(raw_zip) as z:
                            z.extractall(temp_extract)

                        # Find the single wrapper folder
                        extracted_items = list(temp_extract.iterdir())
                        source_root = extracted_items[0] if (len(extracted_items) == 1 and extracted_items[0].is_dir()) else temp_extract

                        target_zip_path.parent.mkdir(parents=True, exist_ok=True)
                        with zipfile.ZipFile(target_zip_path, "w", zipfile.ZIP_DEFLATED) as z_out:
                            for root, dirs, files in os.walk(source_root):
                                if ".git" in dirs:
                                    dirs.remove(".git")
                                for f in files:
                                    full_p = Path(root) / f
                                    arc_p = full_p.relative_to(source_root).as_posix()
                                    z_out.write(full_p, arc_p)

                        return commit_info
                    finally:
                        shutil.rmtree(temp_extract, ignore_errors=True)
        except Exception as api_exc:
            logger.warning("GitHub zipball API download fallback to git clone: {err}", err=str(api_exc))

        # Fallback to shallow git clone
        full_git_url = f"https://github.com/{owner}/{repo}.git"
        return await self.git_provider.fetch_and_package_source(
            full_git_url, branch, target_zip_path, commit_sha, token
        )
