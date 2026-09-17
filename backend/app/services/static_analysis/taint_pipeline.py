# ============================================================
# Taint Analysis Pipeline Integration (Phase 4 Evidence Layer)
# ============================================================

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import networkx as nx
from loguru import logger

from backend.app.services.static_analysis.service import GeneratedArtifactMeta
from taint_analysis.services.taint_service import TaintService


class TaintPipelineService:
    """Executes taint analysis against canonical CPG and packages static evidence."""

    SCHEMA_VERSION = "1.0.0"

    def __init__(self) -> None:
        self.taint_service = TaintService()

    def run_taint_analysis(
        self,
        *,
        cpg: nx.DiGraph,
        workspace: Path,
        scan_id: uuid.UUID,
        snapshot_id: uuid.UUID,
    ) -> GeneratedArtifactMeta:
        """Run taint propagation and attack path extraction on CPG."""
        taint_workspace = workspace / "taint"
        taint_workspace.mkdir(parents=True, exist_ok=True)

        logger.info("Executing taint analysis pipeline for scan {scan_id}", scan_id=scan_id)

        taint_res = self.taint_service.analyze(
            cpg=cpg,
            cpg_job_id=str(scan_id),
            output_dir=taint_workspace,
        )

        artifact_id = uuid.uuid4()
        artifact_file = workspace / f"taint_{artifact_id}.json"

        paths_data = []
        for path in getattr(taint_res, "paths", []):
            paths_data.append(
                {
                    "path_id": path.path_id,
                    "source_id": path.source_id,
                    "sink_id": path.sink_id,
                    "length": path.length,
                    "nodes": path.nodes,
                    "risk_score": path.risk_score,
                    "source_file": getattr(path, "source_file", None),
                    "source_line": getattr(path, "source_line", None),
                    "sink_file": getattr(path, "sink_file", None),
                    "sink_line": getattr(path, "sink_line", None),
                }
            )

        evidence_payload = {
            "schema_version": self.SCHEMA_VERSION,
            "artifact_id": str(artifact_id),
            "scan_id": str(scan_id),
            "source_snapshot_id": str(snapshot_id),
            "artifact_type": "TAINT",
            "tool_name": "taint_engine",
            "tool_version": "1.0.0",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source_count": taint_res.source_count,
            "sink_count": taint_res.sink_count,
            "sanitizer_count": taint_res.sanitizer_count,
            "attack_path_count": len(paths_data),
            "paths": paths_data,
            "taint_rules_version": "1.0.0",
        }

        json_bytes = json.dumps(evidence_payload, indent=2).encode("utf-8")
        artifact_file.write_bytes(json_bytes)

        sha256_hash = hashlib.sha256(json_bytes).hexdigest()

        return GeneratedArtifactMeta(
            artifact_id=artifact_id,
            artifact_type="TAINT",
            schema_version=self.SCHEMA_VERSION,
            artifact_path=artifact_file,
            content_hash=sha256_hash,
            size_bytes=len(json_bytes),
            node_count=taint_res.source_count + taint_res.sink_count,
            edge_count=len(paths_data),
            tool_name="taint_engine",
            tool_version="1.0.0",
            metadata={
                "source_count": taint_res.source_count,
                "sink_count": taint_res.sink_count,
                "sanitizer_count": taint_res.sanitizer_count,
                "path_count": len(paths_data),
            },
        )
