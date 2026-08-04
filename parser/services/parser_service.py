# ============================================================
# Parser Service — Full Pipeline Orchestrator
# ============================================================
# Coordinates: preprocessing → Joern → graph building →
# export → DB metadata storage.
# Designed to run inside a ThreadPoolExecutor so the async
# FastAPI event loop is never blocked.
# ============================================================

from __future__ import annotations

import shutil
import traceback
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import networkx as nx
from loguru import logger

from parser.graph_builder.cpg import CPGBuilder
from parser.graph_builder.serializer import GraphSerializer
from parser.graph_builder.validator import GraphValidator
from parser.joern.config import get_joern_config
from parser.joern.exporter import GraphExporter
from parser.joern.importer import GraphSONImporter
from parser.joern.runner import JoernNotFoundError, JoernRunner
from parser.preprocessing.extractor import SingleFileHandler, ZIPExtractor
from parser.preprocessing.normalizer import Normalizer
from parser.preprocessing.validator import ProjectValidator, ValidationError


@dataclass
class ParseResult:
    """Outcome of a full parse pipeline run."""

    job_id: str
    project_id: str
    status: str                    # "completed" | "failed"
    file_count: int = 0
    function_count: int = 0
    ast_nodes: int = 0
    cfg_nodes: int = 0
    dfg_nodes: int = 0
    total_nodes: int = 0
    total_edges: int = 0
    graph_path: str = ""
    metadata_path: str = ""
    error: str | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "project_id": self.project_id,
            "status": self.status,
            "file_count": self.file_count,
            "function_count": self.function_count,
            "ast_nodes": self.ast_nodes,
            "cfg_nodes": self.cfg_nodes,
            "dfg_nodes": self.dfg_nodes,
            "total_nodes": self.total_nodes,
            "total_edges": self.total_edges,
            "graph_path": self.graph_path,
            "metadata_path": self.metadata_path,
            "error": self.error,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class ParserService:
    """Orchestrates the full C/C++ → CPG pipeline.

    Usage (called from a FastAPI background task)::

        service = ParserService()
        result = service.parse_project(
            job_id=str(uuid.uuid4()),
            project_id=str(upload.project_id),
            source_path=Path("uploads/my_project.zip"),
        )
    """

    def __init__(self) -> None:
        self._config = get_joern_config()
        self._validator = ProjectValidator()
        self._extractor = ZIPExtractor()
        self._single_file = SingleFileHandler()
        self._normalizer = Normalizer()
        self._importer = GraphSONImporter()
        self._cpg_builder = CPGBuilder()
        self._serializer = GraphSerializer()
        self._graph_validator = GraphValidator()
        self._exporter = GraphExporter()

    # ── Public API ─────────────────────────────────────────

    def parse_project(
        self,
        job_id: str,
        project_id: str,
        source_path: Path,
    ) -> ParseResult:
        """Run the full pipeline synchronously.

        Intended to be called inside ``loop.run_in_executor()`` so the
        JVM startup and Joern subprocess don't block the event loop.

        Args:
            job_id:      Unique identifier for this parse job.
            project_id:  Project UUID (used to namespace output dirs).
            source_path: Path to the uploaded file (.c, .cpp, .zip, or dir).

        Returns:
            A :class:`ParseResult` with status and graph statistics.
        """
        result = ParseResult(job_id=job_id, project_id=project_id, status="running")
        workspace = self._config.graphs_path / project_id

        try:
            # ── Step 1 : Prepare source tree ──────────────
            project_dir = self._prepare_source(source_path, workspace)

            # ── Step 2 : Validate & discover source files ─
            metadata = self._validator.validate(project_dir)
            result.file_count = metadata.file_count

            # ── Step 3 : Normalise files ──────────────────
            self._normalizer.normalize_project(project_dir, metadata.source_files)

            # ── Step 4 : Run Joern parse ──────────────────
            cpg_path = workspace / "cpg.bin"
            export_dir = workspace / "graphson"
            self._run_joern(project_dir, cpg_path, export_dir)

            # ── Step 5 : Import GraphSON ───────────────────
            raw = self._importer.load(export_dir)

            # ── Step 6 : Build CPG ─────────────────────────
            cpg, ast, cfg, dfg = self._cpg_builder.build_from_raw(raw)

            # ── Step 7 : Validate graph ────────────────────
            report = self._graph_validator.validate(cpg)
            if report.has_errors:
                raise RuntimeError(
                    f"Graph validation failed: {report.error_codes}"
                )

            # ── Step 8 : Compute statistics ────────────────
            stats = self._serializer.statistics(cpg, ast, cfg, dfg)
            result.function_count = stats["function_count"]
            result.ast_nodes = stats["ast_nodes"]
            result.cfg_nodes = stats["cfg_nodes"]
            result.dfg_nodes = stats["dfg_nodes"]
            result.total_nodes = stats["total_nodes"]
            result.total_edges = stats["total_edges"]

            # ── Step 9 : Export to disk ────────────────────
            full_meta = {**stats, **metadata.to_dict(), "validation": report.to_dict()}
            graph_path, meta_path = self._exporter.export(cpg, workspace, full_meta)
            result.graph_path = str(graph_path)
            result.metadata_path = str(meta_path)

            result.status = "completed"
            result.completed_at = datetime.now(timezone.utc)
            logger.info(
                "Parse job {id} completed — nodes={n} edges={e}",
                id=job_id,
                n=result.total_nodes,
                e=result.total_edges,
            )

        except ValidationError as e:
            result.status = "failed"
            result.error = f"Validation error: {e}"
            logger.warning("Parse job {id} validation error: {e}", id=job_id, e=e)
        except JoernNotFoundError as e:
            result.status = "failed"
            result.error = str(e)
            logger.error("Parse job {id} — Joern not found: {e}", id=job_id, e=e)
        except Exception as e:
            result.status = "failed"
            result.error = f"{type(e).__name__}: {e}"
            logger.error(
                "Parse job {id} failed: {e}\n{tb}",
                id=job_id,
                e=e,
                tb=traceback.format_exc(),
            )
        finally:
            result.completed_at = result.completed_at or datetime.now(timezone.utc)

        return result

    # ── Private helpers ────────────────────────────────────

    def _prepare_source(self, source_path: Path, workspace: Path) -> Path:
        """Extract ZIP or wrap single file; return the project root directory."""
        workspace.mkdir(parents=True, exist_ok=True)
        ext = source_path.suffix.lower()
        if ext == ".zip":
            return self._extractor.extract(source_path, workspace / "src")
        elif ext in {".c", ".cpp", ".cc", ".h", ".hpp"}:
            return self._single_file.wrap(source_path, workspace / "src")
        elif source_path.is_dir():
            return source_path
        else:
            raise ValidationError(f"Unsupported source format: '{ext}'")

    def _run_joern(self, project_dir: Path, cpg_path: Path, export_dir: Path) -> None:
        """Run joern-parse then joern-export, handling missing Joern gracefully."""
        try:
            runner = JoernRunner(self._config)
        except JoernNotFoundError:
            raise  # Re-raise so the caller sets status = "failed"

        runner.parse(project_dir, cpg_path)
        runner.export(cpg_path, export_dir, repr="all", fmt="graphson")
