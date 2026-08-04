# ============================================================
# Parser Router — Async CPG generation jobs
# ============================================================
# POST /api/v1/parse        → queue a parse job
# GET  /api/v1/parse/{id}   → check job status + stats
# GET  /api/v1/parse/{id}/graph → fetch graph JSON for viewer
# ============================================================

from __future__ import annotations

import asyncio
import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException

from backend.app.config import get_settings
from backend.app.schemas import (
    GraphEdgeSchema,
    GraphNodeSchema,
    GraphResponse,
    ParseJobResponse,
    ParseRequest,
    ParseStatusResponse,
)
from parser.services.parser_service import ParseResult, ParserService

router = APIRouter(prefix="/parse", tags=["Parser"])

# ── In-memory job store (swapped for DB queries in Phase 3) ─
_jobs: dict[str, ParseResult] = {}
_executor = ThreadPoolExecutor(max_workers=2)


# ── POST /parse ────────────────────────────────────────────


@router.post(
    "",
    response_model=ParseJobResponse,
    status_code=202,
    summary="Queue a CPG parse job",
    description=(
        "Launches an async Joern parse on the specified upload. "
        "Returns immediately with a job_id. Poll GET /parse/{job_id} for results."
    ),
)
async def queue_parse_job(
    body: ParseRequest,
    background_tasks: BackgroundTasks,
) -> ParseJobResponse:
    settings = get_settings()
    job_id = uuid.uuid4()

    # Locate the uploaded file on disk
    # The upload router stored the file in uploads/ — we look it up by upload_id
    upload_dir = settings.upload_path
    # Find file matching the upload_id pattern (hex prefix of UUID)
    upload_id_hex = body.upload_id.hex
    matched: list[Path] = list(upload_dir.glob(f"{upload_id_hex}*"))
    if not matched:
        # Try full path scan for any filename containing the upload_id
        all_uploads = list(upload_dir.iterdir())
        matched = [f for f in all_uploads if upload_id_hex in f.name]

    if not matched:
        raise HTTPException(
            status_code=404,
            detail=f"Upload {body.upload_id} not found in uploads directory.",
        )

    source_path = matched[0]
    project_id = str(body.project_id or uuid.uuid4())
    job_id_str = str(job_id)

    # Seed the job in the store immediately so GET can find it
    _jobs[job_id_str] = ParseResult(
        job_id=job_id_str,
        project_id=project_id,
        status="queued",
        started_at=datetime.now(timezone.utc),
    )

    # Run in background (ThreadPoolExecutor keeps event loop free)
    background_tasks.add_task(
        _run_parse_job,
        job_id=job_id_str,
        project_id=project_id,
        source_path=source_path,
    )

    return ParseJobResponse(
        job_id=job_id,
        status="queued",
        message=f"Parse job queued. Poll GET /api/v1/parse/{job_id} for status.",
    )


# ── GET /parse/{job_id} ────────────────────────────────────


@router.get(
    "/{job_id}",
    response_model=ParseStatusResponse,
    summary="Get parse job status",
    description="Returns the current status and graph statistics for a parse job.",
)
async def get_parse_status(job_id: uuid.UUID) -> ParseStatusResponse:
    result = _jobs.get(str(job_id))
    if not result:
        raise HTTPException(status_code=404, detail=f"Parse job {job_id} not found.")

    return ParseStatusResponse(
        job_id=job_id,
        project_id=uuid.UUID(result.project_id),
        status=result.status,
        file_count=result.file_count,
        function_count=result.function_count,
        ast_nodes=result.ast_nodes,
        cfg_nodes=result.cfg_nodes,
        dfg_nodes=result.dfg_nodes,
        total_nodes=result.total_nodes,
        total_edges=result.total_edges,
        graph_path=result.graph_path,
        metadata_path=result.metadata_path,
        error=result.error,
        started_at=result.started_at,
        completed_at=result.completed_at,
    )


# ── GET /parse/{job_id}/graph ──────────────────────────────


@router.get(
    "/{job_id}/graph",
    response_model=GraphResponse,
    summary="Get graph JSON for viewer",
    description=(
        "Returns the full CPG as nodes + edges for the frontend graph viewer. "
        "Only available when status == 'completed'."
    ),
)
async def get_graph(job_id: uuid.UUID) -> GraphResponse:
    result = _jobs.get(str(job_id))
    if not result:
        raise HTTPException(status_code=404, detail=f"Parse job {job_id} not found.")
    if result.status != "completed":
        raise HTTPException(
            status_code=425,
            detail=f"Graph not ready. Job status is '{result.status}'.",
        )
    if not result.graph_path or not Path(result.graph_path).exists():
        raise HTTPException(status_code=404, detail="Graph file not found on disk.")

    graph_data = json.loads(Path(result.graph_path).read_text())
    meta_data: dict = {}
    if result.metadata_path and Path(result.metadata_path).exists():
        meta_data = json.loads(Path(result.metadata_path).read_text())

    nodes = [
        GraphNodeSchema(
            id=n["id"],
            label=n.get("label"),
            code=n.get("CODE") or n.get("code"),
            line_number=n.get("lineNumber") or n.get("line_number"),
            filename=n.get("filename") or n.get("FILENAME"),
            layers=n.get("_layers", []),
        )
        for n in graph_data.get("nodes", [])
    ]
    edges = [
        GraphEdgeSchema(
            source=e["source"],
            target=e["target"],
            label=e.get("label"),
            layer=e.get("layer"),
            variable=e.get("variable"),
        )
        for e in graph_data.get("edges", [])
    ]

    return GraphResponse(
        job_id=job_id,
        nodes=nodes,
        edges=edges,
        statistics=meta_data,
    )


# ── Background task ────────────────────────────────────────


async def _run_parse_job(
    job_id: str,
    project_id: str,
    source_path: Path,
) -> None:
    """Runs the parser in a thread pool so the event loop stays free."""
    service = ParserService()
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        _executor,
        service.parse_project,
        job_id,
        project_id,
        source_path,
    )
    _jobs[job_id] = result
