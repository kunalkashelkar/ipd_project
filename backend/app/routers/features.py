# ============================================================
# Features Router — Async PyTorch Geometric Dataset Jobs
# ============================================================
# POST /api/v1/features/build   → queue a dataset generation
# GET  /api/v1/features/{id}    → check job status + summary
# ============================================================

from __future__ import annotations

import asyncio
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException

from backend.app.config import get_settings
from backend.app.schemas import (
    DatasetRequest,
    DatasetJobResponse,
    DatasetStatusResponse,
)
from feature_engineering.services.feature_service import FeatureService

router = APIRouter(prefix="/features", tags=["Feature Engineering"])

# ── In-memory job store ─────
_dataset_jobs: dict[str, dict] = {}
_executor = ThreadPoolExecutor(max_workers=2)

@router.post(
    "/build",
    response_model=DatasetJobResponse,
    status_code=202,
    summary="Queue a PyTorch Geometric Dataset build",
)
async def queue_dataset_build(
    body: DatasetRequest,
    background_tasks: BackgroundTasks,
) -> DatasetJobResponse:
    settings = get_settings()
    job_id = uuid.uuid4()
    job_id_str = str(job_id)
    project_id_str = str(body.project_id)

    # Note: Using the project_id to find graphs
    # Normally these paths are strictly mapped in DB
    graph_dir = settings.graphs_path if hasattr(settings, "graphs_path") else (
        Path(settings.graph_output_dir)
        if hasattr(settings, "graph_output_dir")
        else Path("./graphs")
    )
    
    project_graph_dir = graph_dir / project_id_str
    
    if not project_graph_dir.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                f"No processed graphs directory found for project {body.project_id}. "
                "Ensure parsed graphs have gone through anomaly and taint analyses."
            ),
        )

    output_dir = Path("./datasets/feature_tensors") / project_id_str

    _dataset_jobs[job_id_str] = {
        "job_id": job_id_str,
        "project_id": project_id_str,
        "status": "queued",
        "started_at": datetime.now(timezone.utc),
        "processed_graphs": 0,
        "failed_graphs": 0,
        "total_graphs": 0,
    }

    background_tasks.add_task(
        _run_dataset_job,
        job_id_str=job_id_str,
        project_id_str=project_id_str,
        graphs_dir=project_graph_dir,
        output_dir=output_dir,
    )

    return DatasetJobResponse(
        dataset_job_id=job_id,
        project_id=body.project_id,
        status="queued",
        message=f"Dataset processing queued. Poll GET /api/v1/features/{job_id}."
    )


@router.get(
    "/{job_id}",
    response_model=DatasetStatusResponse,
    summary="Get dataset job status",
)
async def get_dataset_status(job_id: uuid.UUID) -> DatasetStatusResponse:
    result = _dataset_jobs.get(str(job_id))
    if not result:
        raise HTTPException(status_code=404, detail=f"Dataset job {job_id} not found.")

    return DatasetStatusResponse(
        dataset_job_id=job_id,
        project_id=uuid.UUID(result["project_id"]),
        status=result.get("status", "unknown"),
        processed_graphs=result.get("processed_graphs", 0),
        failed_graphs=result.get("failed_graphs", 0),
        total_graphs=result.get("total_graphs", 0),
        dataset_path=result.get("dataset_path"),
        error=result.get("error_message"),
        started_at=result.get("started_at"),
        completed_at=result.get("completed_at"),
    )


async def _run_dataset_job(
    job_id_str: str,
    project_id_str: str,
    graphs_dir: Path,
    output_dir: Path,
) -> None:
    service = FeatureService(use_mock_codebert=True)
    loop = asyncio.get_event_loop()
    
    _dataset_jobs[job_id_str]["status"] = "running"
    
    try:
        report = await loop.run_in_executor(
            _executor,
            service.process_project,
            project_id_str,
            graphs_dir,
            output_dir,
        )
        
        _dataset_jobs[job_id_str]["status"] = "completed"
        _dataset_jobs[job_id_str]["processed_graphs"] = report["processed"]
        _dataset_jobs[job_id_str]["failed_graphs"] = report["failed"]
        _dataset_jobs[job_id_str]["total_graphs"] = report["total"]
        _dataset_jobs[job_id_str]["dataset_path"] = report["dataset_path"]
        _dataset_jobs[job_id_str]["completed_at"] = datetime.now(timezone.utc)
        
    except Exception as e:
        _dataset_jobs[job_id_str]["status"] = "failed"
        _dataset_jobs[job_id_str]["error_message"] = str(e)
        _dataset_jobs[job_id_str]["completed_at"] = datetime.now(timezone.utc)
