# ============================================================
# Taint Router — Async taint analysis jobs
# ============================================================
# POST /api/v1/taint/analyze   → queue a taint analysis
# GET  /api/v1/taint/{id}      → check job status + summary
# GET  /api/v1/taint/{id}/report → full attack paths report
# GET  /api/v1/taint/{id}/graph  → security-annotated graph
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
    AttackPathSchema,
    TaintJobResponse,
    TaintReportResponse,
    TaintRequest,
    TaintStatusResponse,
    GraphNodeSchema,
    GraphEdgeSchema,
    GraphResponse,
)
from taint_analysis.models.result import TaintResult
from taint_analysis.services.taint_service import TaintService

router = APIRouter(prefix="/taint", tags=["Taint Analysis"])

# ── In-memory job store (same pattern as parser router) ─────
_taint_jobs: dict[str, TaintResult] = {}
_executor = ThreadPoolExecutor(max_workers=2)


# ── POST /taint/analyze ─────────────────────────────────────

@router.post(
    "/analyze",
    response_model=TaintJobResponse,
    status_code=202,
    summary="Queue a taint analysis job",
    description=(
        "Runs taint analysis on the graph produced by the given CPG parse job. "
        "Returns immediately with a taint_job_id. Poll GET /taint/{taint_job_id} for results."
    ),
)
async def queue_taint_analysis(
    body: TaintRequest,
    background_tasks: BackgroundTasks,
) -> TaintJobResponse:
    settings = get_settings()
    taint_job_id = uuid.uuid4()
    taint_job_str = str(taint_job_id)
    cpg_job_id_str = str(body.cpg_job_id)

    # Locate the graph.json written by Phase 2
    graph_dir = settings.graphs_path if hasattr(settings, "graphs_path") else (
        Path(settings.graph_output_dir)
        if hasattr(settings, "graph_output_dir")
        else Path("./graphs")
    )

    # Look for project graph directories containing our cpg_job_id
    graph_json: Path | None = None
    for candidate in graph_dir.rglob("graph.json"):
        graph_json = candidate
        break  # For Phase 3 we pick the most recent; Phase 8 will link by job ID

    if graph_json is None or not graph_json.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                f"No graph.json found for CPG job {body.cpg_job_id}. "
                "Ensure the parse job completed successfully first."
            ),
        )

    output_dir = graph_json.parent

    # Seed the job store
    _taint_jobs[taint_job_str] = TaintResult(
        job_id=taint_job_str,
        cpg_job_id=cpg_job_id_str,
        status="queued",
        started_at=datetime.now(timezone.utc),
    )

    background_tasks.add_task(
        _run_taint_job,
        taint_job_id=taint_job_str,
        cpg_job_id=cpg_job_id_str,
        graph_json_path=graph_json,
        output_dir=output_dir,
    )

    return TaintJobResponse(
        taint_job_id=taint_job_id,
        cpg_job_id=body.cpg_job_id,
        status="queued",
        message=f"Taint analysis queued. Poll GET /api/v1/taint/{taint_job_id} for results.",
    )


# ── GET /taint/{taint_job_id} ───────────────────────────────

@router.get(
    "/{taint_job_id}",
    response_model=TaintStatusResponse,
    summary="Get taint job status",
)
async def get_taint_status(taint_job_id: uuid.UUID) -> TaintStatusResponse:
    result = _taint_jobs.get(str(taint_job_id))
    if not result:
        raise HTTPException(status_code=404, detail=f"Taint job {taint_job_id} not found.")

    return TaintStatusResponse(
        taint_job_id=taint_job_id,
        cpg_job_id=uuid.UUID(result.cpg_job_id),
        status=result.status,
        source_count=result.source_count,
        sink_count=result.sink_count,
        sanitizer_count=result.sanitizer_count,
        tainted_node_count=result.tainted_node_count,
        attack_path_count=result.attack_path_count,
        critical_path_count=result.critical_path_count,
        high_path_count=result.high_path_count,
        medium_path_count=result.medium_path_count,
        low_path_count=result.low_path_count,
        security_graph_path=result.security_graph_path,
        taint_report_path=result.taint_report_path,
        error=result.error,
        started_at=result.started_at,
        completed_at=result.completed_at,
    )


# ── GET /taint/{taint_job_id}/report ────────────────────────

@router.get(
    "/{taint_job_id}/report",
    response_model=TaintReportResponse,
    summary="Get full taint report with attack paths",
)
async def get_taint_report(taint_job_id: uuid.UUID) -> TaintReportResponse:
    result = _taint_jobs.get(str(taint_job_id))
    if not result:
        raise HTTPException(status_code=404, detail=f"Taint job {taint_job_id} not found.")
    if result.status != "completed":
        raise HTTPException(425, detail=f"Report not ready — status is '{result.status}'.")

    # Load from file if attack_paths is empty (serialized across restart)
    if not result.attack_paths and result.taint_report_path:
        report_data = json.loads(Path(result.taint_report_path).read_text())
        attack_paths_raw = report_data.get("attack_paths", [])
    else:
        attack_paths_raw = [p.to_dict() for p in result.attack_paths]

    paths = [AttackPathSchema(**p) for p in attack_paths_raw]

    return TaintReportResponse(
        taint_job_id=taint_job_id,
        cpg_job_id=uuid.UUID(result.cpg_job_id),
        summary=result.severity_summary(),
        attack_paths=paths,
    )


# ── GET /taint/{taint_job_id}/graph ─────────────────────────

@router.get(
    "/{taint_job_id}/graph",
    response_model=GraphResponse,
    summary="Get security-annotated graph for viewer",
)
async def get_security_graph(taint_job_id: uuid.UUID) -> GraphResponse:
    result = _taint_jobs.get(str(taint_job_id))
    if not result:
        raise HTTPException(status_code=404, detail=f"Taint job {taint_job_id} not found.")
    if result.status != "completed":
        raise HTTPException(425, detail=f"Graph not ready — status is '{result.status}'.")
    if not result.security_graph_path or not Path(result.security_graph_path).exists():
        raise HTTPException(404, detail="Security graph file not found on disk.")

    graph_data = json.loads(Path(result.security_graph_path).read_text())

    nodes = [
        GraphNodeSchema(
            id=n["id"],
            label=n.get("label"),
            code=n.get("CODE") or n.get("code"),
            line_number=n.get("lineNumber") or n.get("line_number"),
            filename=n.get("filename"),
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

    # Include taint stats in the statistics field
    stats: dict = {
        "source_count":       result.source_count,
        "sink_count":         result.sink_count,
        "tainted_node_count": result.tainted_node_count,
        "attack_path_count":  result.attack_path_count,
        "severity_breakdown": result.severity_summary(),
    }

    return GraphResponse(job_id=taint_job_id, nodes=nodes, edges=edges, statistics=stats)


# ── Background task ─────────────────────────────────────────

async def _run_taint_job(
    taint_job_id: str,
    cpg_job_id: str,
    graph_json_path: Path,
    output_dir: Path,
) -> None:
    service = TaintService()
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        _executor,
        service.analyze_from_graph_json,
        graph_json_path,
        cpg_job_id,
        output_dir,
    )
    result.job_id = taint_job_id
    _taint_jobs[taint_job_id] = result
