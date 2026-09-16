# ============================================================
# Repository Synchronization Celery Tasks (Phase 3)
# ============================================================

from __future__ import annotations

import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger
from sqlalchemy import select

from backend.app.database.session import async_session_factory
from backend.app.models.git_meta import RepositoryBranch, RepositoryCommit
from backend.app.models.project import Project
from backend.app.models.repository import Repository
from backend.app.models.source_snapshot import SourceSnapshot
from backend.app.services.vcs import get_vcs_provider
from backend.app.storage.service import StorageService
from backend.app.workers.base_task import AsyncCeleryTask
from backend.app.workers.celery_app import celery_app
from backend.app.workers.snapshot_tasks import process_source_snapshot_task


@celery_app.task(bind=True, base=AsyncCeleryTask, name="sync_repository")
async def sync_repository_task(
    self,
    repository_id: str,
    branch_name: str | None = None,
    auth_token: str | None = None,
):
    """Worker task that executes Git/GitHub repository sync and triggers preprocessing."""
    logger.info("Starting repository sync for repo {id}", id=repository_id)

    repo_uuid = uuid.UUID(repository_id)
    async with async_session_factory() as db:
        stmt = (
            select(Repository, Project)
            .join(Project, Repository.project_id == Project.id)
            .where(Repository.id == repo_uuid)
        )
        res = await db.execute(stmt)
        row = res.first()
        if not row:
            logger.error("Repository {id} not found", id=repository_id)
            return

        repo, project = row
        repo.status = "syncing"
        await db.commit()

        target_branch = branch_name or repo.branch or "main"
        provider = get_vcs_provider(repo.provider)

        temp_zip = Path(tempfile.mktemp(suffix=".zip", prefix="repo_sync_"))
        try:
            # 1. Fetch source archive and commit metadata
            commit_info = await provider.fetch_and_package_source(
                repo_url=repo.repository_url or "",
                branch=target_branch,
                target_zip_path=temp_zip,
                token=auth_token,
            )

            # 2. Get or create RepositoryCommit
            commit_sha = commit_info["commit_sha"]
            c_stmt = select(RepositoryCommit).where(
                RepositoryCommit.repository_id == repo.id,
                RepositoryCommit.commit_sha == commit_sha,
            )
            c_res = await db.execute(c_stmt)
            commit = c_res.scalar_one_or_none()
            if not commit:
                commit = RepositoryCommit(
                    id=uuid.uuid4(),
                    repository_id=repo.id,
                    commit_sha=commit_sha,
                    author_name=commit_info["author_name"],
                    author_email=commit_info["author_email"],
                    message=commit_info["message"],
                    committed_at=commit_info["committed_at"],
                )
                db.add(commit)
                await db.flush()

            # 3. Update or create RepositoryBranch
            b_stmt = select(RepositoryBranch).where(
                RepositoryBranch.repository_id == repo.id,
                RepositoryBranch.name == target_branch,
            )
            b_res = await db.execute(b_stmt)
            branch_obj = b_res.scalar_one_or_none()
            if not branch_obj:
                branch_obj = RepositoryBranch(
                    id=uuid.uuid4(),
                    repository_id=repo.id,
                    name=target_branch,
                    is_default=(target_branch in ("main", "master")),
                    head_commit_sha=commit_sha,
                )
                db.add(branch_obj)
            else:
                branch_obj.head_commit_sha = commit_sha

            # 4. Create new immutable SourceSnapshot
            snapshot_id = uuid.uuid4()
            storage = StorageService()
            archive_key = StorageService.snapshot_archive_key(
                org_id=project.organization_id,
                project_id=project.id,
                snapshot_id=snapshot_id,
                ext=".zip",
            )

            zip_bytes = temp_zip.read_bytes()
            await storage.save_object(zip_bytes, archive_key)

            snapshot = SourceSnapshot(
                id=snapshot_id,
                project_id=project.id,
                repository_id=repo.id,
                repository_commit_id=commit.id,
                source_type=repo.provider,
                source_version=commit_sha,
                content_hash=commit_sha,
                artifact_uri=archive_key,
                status="pending",
                file_count=0,
                total_bytes=len(zip_bytes),
                preprocessing_version="v1.0.0",
            )
            db.add(snapshot)

            # Update repository state
            repo.status = "connected"
            repo.commit_sha = commit_sha
            repo.branch = target_branch
            repo.last_synced_at = datetime.now(timezone.utc)
            await db.commit()

            # 5. Enqueue preprocessing task in Celery
            process_source_snapshot_task.delay(
                str(snapshot.id),
                str(project.organization_id),
                str(project.id),
            )

            logger.info(
                "Repository {repo_id} synced successfully. Created snapshot {snap_id}",
                repo_id=repository_id,
                snap_id=snapshot_id,
            )
            return {
                "repository_id": str(repo.id),
                "snapshot_id": str(snapshot.id),
                "commit_sha": commit_sha,
                "status": "connected",
            }

        except Exception as exc:
            logger.exception("Repository sync failed for {id}: {err}", id=repository_id, err=str(exc))
            repo.status = "failed"
            await db.commit()
            raise
        finally:
            if temp_zip.exists():
                temp_zip.unlink(missing_ok=True)
