# ============================================================
# Phase 3 Snapshot & Repository Schemas
# ============================================================

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any
from typing_extensions import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SourceSnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    public_id: str | None = None
    project_id: uuid.UUID
    repository_id: uuid.UUID | None = None
    repository_commit_id: uuid.UUID | None = None
    source_type: str
    source_version: str | None = None
    content_hash: str
    status: str
    file_count: int = 0
    total_bytes: int = 0
    detected_languages: dict[str, Any] | None = None
    preprocessing_version: str = "v1.0.0"
    created_at: datetime
    completed_at: datetime | None = None
    failure_reason: str | None = None


class SourceSnapshotListResponse(BaseModel):
    items: list[SourceSnapshotResponse]
    total: int
    page: int = 1
    page_size: int = 50


class SourceFileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_snapshot_id: uuid.UUID
    relative_path: str
    language: str | None = None
    size_bytes: int
    content_hash: str
    line_count: int
    validation_status: str
    preprocessing_status: str
    is_binary: bool


class SourceFileListResponse(BaseModel):
    items: list[SourceFileResponse]
    total: int
    page: int = 1
    page_size: int = 50


class FunctionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_file_id: uuid.UUID
    function_id: str
    qualified_name: str | None = None
    name: str
    language: str | None = None
    start_line: int
    end_line: int
    signature: str | None = None
    token_count: int = 0
    duplicate_group_id: str | None = None


class FunctionListResponse(BaseModel):
    items: list[FunctionResponse]
    total: int


class SourceFileContentResponse(BaseModel):
    relative_path: str
    content: str
    language: str | None = None
    line_count: int
    size_bytes: int
    is_binary: bool = False


class RepositoryConnectRequest(BaseModel):
    provider: str = Field(..., description="VCS provider: 'github' or 'git'")
    repository_url: str = Field(..., min_length=3, description="Repository URL or owner/repo slug")
    branch: str = Field(default="main", description="Target branch")
    auth_token: str | None = Field(default=None, description="Optional GitHub access token for private repositories")
    display_name: str | None = Field(default=None, description="Optional display name")

    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "repo_url" in data and "repository_url" not in data:
                data["repository_url"] = data["repo_url"]
            if "default_branch" in data and "branch" not in data:
                data["branch"] = data["default_branch"]
            if "access_token" in data and "auth_token" not in data:
                data["auth_token"] = data["access_token"]
            if data.get("provider") in ("local_git", "git"):
                data["provider"] = "git"
        return data


class RepositoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    provider: str
    repository_url: str | None = None
    repo_url: str | None = None
    branch: str | None = None
    selected_branch: str | None = None
    default_branch: str | None = None
    commit_sha: str | None = None
    current_commit_sha: str | None = None
    display_name: str | None = None
    status: str
    last_synced_at: datetime | None = None
    created_at: datetime

    @model_validator(mode="after")
    def sync_aliases(self) -> Self:
        if not self.repo_url and self.repository_url:
            self.repo_url = self.repository_url
        if not self.selected_branch and self.branch:
            self.selected_branch = self.branch
        if not self.default_branch and self.branch:
            self.default_branch = self.branch
        if not self.current_commit_sha and self.commit_sha:
            self.current_commit_sha = self.commit_sha
        if not self.display_name and self.repository_url:
            self.display_name = self.repository_url.split("/")[-1].replace(".git", "")
        return self



class RepositoryListResponse(BaseModel):
    items: list[RepositoryResponse]
    total: int


class BranchResponse(BaseModel):
    name: str
    is_default: bool = False
    head_commit_sha: str | None = None


class CommitResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    commit_sha: str
    author_name: str | None = None
    author_email: str | None = None
    message: str | None = None
    committed_at: datetime
