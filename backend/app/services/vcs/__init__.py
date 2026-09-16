# ============================================================
# VCS Package (Phase 3)
# ============================================================

from backend.app.services.vcs.base import CommitInfo, RepositoryProvider
from backend.app.services.vcs.git_provider import GitProvider
from backend.app.services.vcs.github_provider import GitHubProvider


def get_vcs_provider(provider_type: str) -> RepositoryProvider:
    """Factory retrieving appropriate VCS provider implementation."""
    p_type = provider_type.strip().lower()
    if p_type == "github":
        return GitHubProvider()
    elif p_type in ("git", "local_git", "gitlab", "bitbucket"):
        return GitProvider()
    raise ValueError(f"Unsupported VCS provider type: {provider_type}")


__all__ = [
    "CommitInfo",
    "RepositoryProvider",
    "GitProvider",
    "GitHubProvider",
    "get_vcs_provider",
]
