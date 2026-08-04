# ============================================================
# Taint Analysis — Full Pipeline Service
# ============================================================
# Orchestrates: rule loading → detection → propagation →
# path extraction → scoring → annotation → export
# ============================================================

from __future__ import annotations

import json
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import networkx as nx
from loguru import logger

from taint_analysis.engine.annotator import GraphAnnotator
from taint_analysis.engine.attack_path import AttackPathExtractor
from taint_analysis.engine.propagation import TaintPropagator
from taint_analysis.engine.risk_score import RiskScorer
from taint_analysis.engine.rule_loader import RuleLoader
from taint_analysis.engine.sanitizer_detector import SanitizerDetector
from taint_analysis.engine.sink_detector import SinkDetector
from taint_analysis.engine.source_detector import SourceDetector
from taint_analysis.models.path import AttackPath
from taint_analysis.models.result import TaintResult


class TaintService:
    """Orchestrates the full taint analysis pipeline on a parsed CPG.

    Designed to be called from a FastAPI background task (in a thread pool)
    or directly from tests by passing a NetworkX DiGraph.
    """

    def __init__(self, rules: RuleLoader | None = None) -> None:
        self._rules        = rules or RuleLoader()
        self._src_det      = SourceDetector()
        self._snk_det      = SinkDetector()
        self._san_det      = SanitizerDetector()
        self._propagator   = TaintPropagator()
        self._path_ext     = AttackPathExtractor()
        self._scorer       = RiskScorer()
        self._annotator    = GraphAnnotator()

    # ── Public API ─────────────────────────────────────────

    def analyze(
        self,
        cpg: nx.DiGraph,
        cpg_job_id: str,
        output_dir: Path,
    ) -> TaintResult:
        """Run the full taint analysis pipeline on *cpg*.

        Args:
            cpg:         The NetworkX DiGraph produced by Phase 2.
            cpg_job_id:  ID of the corresponding ParserJob (for linking).
            output_dir:  Directory where outputs are written.

        Returns:
            A :class:`TaintResult` with all statistics and output paths.
        """
        job_id = str(uuid.uuid4())
        result = TaintResult(
            job_id=job_id,
            cpg_job_id=cpg_job_id,
            status="running",
            started_at=datetime.now(timezone.utc),
        )

        try:
            output_dir.mkdir(parents=True, exist_ok=True)

            # ── Step 1: Detect sources, sinks, sanitizers ──
            logger.info("[TaintService] Step 1/7 — Detecting sources, sinks, sanitizers")
            source_ids    = self._src_det.detect(cpg, self._rules)
            sink_ids      = self._snk_det.detect(cpg, self._rules)
            sanitizer_ids = self._san_det.detect(cpg, self._rules)

            result.source_count    = len(source_ids)
            result.sink_count      = len(sink_ids)
            result.sanitizer_count = len(sanitizer_ids)

            logger.info(
                "[TaintService] Detected — sources={s} sinks={sk} sanitizers={san}",
                s=result.source_count,
                sk=result.sink_count,
                san=result.sanitizer_count,
            )

            # ── Step 2: Taint propagation ──────────────────
            logger.info("[TaintService] Step 2/7 — Propagating taint")
            taint = self._propagator.propagate(
                cpg,
                source_ids=source_ids,
                sanitizer_ids=set(sanitizer_ids),
            )
            result.tainted_node_count = sum(1 for t in taint.values() if t.is_tainted)

            # ── Step 3: Attack path extraction ─────────────
            logger.info("[TaintService] Step 3/7 — Extracting attack paths")
            attack_paths = self._path_ext.extract(
                cpg,
                source_ids=source_ids,
                sink_ids=sink_ids,
                sanitizer_ids=set(sanitizer_ids),
                taint=taint,
            )

            # ── Step 4: Risk scoring ───────────────────────
            logger.info("[TaintService] Step 4/7 — Scoring attack paths")
            sink_to_source_count = self._count_sources_per_sink(attack_paths)
            path_risk_scores: dict[str, tuple[float, str]] = {}

            for path in attack_paths:
                multi = sink_to_source_count.get(path.sink_node_id, 1) > 1
                score, level = self._scorer.score_and_classify(path, multi_source=multi)
                path.risk_score = score
                path.severity   = level
                path_risk_scores[path.path_id] = (score, level)

            # ── Step 5: Annotate CPG ───────────────────────
            logger.info("[TaintService] Step 5/7 — Annotating CPG")
            annotated_cpg = self._annotator.annotate(
                cpg, taint, attack_paths, path_risk_scores
            )

            # ── Step 6: Compute severity breakdown ─────────
            severity_counts = self._scorer.count_by_severity(attack_paths)
            result.attack_path_count   = len(attack_paths)
            result.critical_path_count = severity_counts.get("CRITICAL", 0)
            result.high_path_count     = severity_counts.get("HIGH", 0)
            result.medium_path_count   = severity_counts.get("MEDIUM", 0)
            result.low_path_count      = severity_counts.get("LOW", 0)
            result.safe_path_count     = severity_counts.get("SAFE", 0)
            result.attack_paths        = attack_paths

            # ── Step 7: Export outputs ─────────────────────
            logger.info("[TaintService] Step 6/7 — Exporting security graph")
            sg_path, report_path = self._export(
                annotated_cpg, attack_paths, result, output_dir
            )
            result.security_graph_path = str(sg_path)
            result.taint_report_path   = str(report_path)

            result.status       = "completed"
            result.completed_at = datetime.now(timezone.utc)
            logger.info(
                "[TaintService] Analysis complete — job={id} paths={n} critical={c}",
                id=job_id,
                n=result.attack_path_count,
                c=result.critical_path_count,
            )

        except Exception as e:
            result.status       = "failed"
            result.error        = f"{type(e).__name__}: {e}"
            result.completed_at = datetime.now(timezone.utc)
            logger.error(
                "[TaintService] Failed: {e}\n{tb}",
                e=e,
                tb=traceback.format_exc(),
            )

        return result

    def analyze_from_graph_json(
        self,
        graph_json_path: Path,
        cpg_job_id: str,
        output_dir: Path,
    ) -> TaintResult:
        """Load a graph.json from disk and run taint analysis.

        Convenience method for the background task — loads the graph
        that was exported by Phase 2's ParserService.
        """
        cpg = self._load_graph_json(graph_json_path)
        return self.analyze(cpg, cpg_job_id, output_dir)

    # ── Private helpers ────────────────────────────────────

    def _load_graph_json(self, path: Path) -> nx.DiGraph:
        """Reconstruct a NetworkX DiGraph from the Phase 2 graph.json format."""
        data = json.loads(path.read_text(encoding="utf-8"))
        g = nx.DiGraph()
        for node in data.get("nodes", []):
            nid = node.pop("id")
            g.add_node(nid, **node)
        for edge in data.get("edges", []):
            src = edge.pop("source")
            tgt = edge.pop("target")
            g.add_edge(src, tgt, **edge)
        logger.debug(
            "Loaded graph.json — nodes={n} edges={e}",
            n=g.number_of_nodes(),
            e=g.number_of_edges(),
        )
        return g

    def _export(
        self,
        cpg: nx.DiGraph,
        paths: list[AttackPath],
        result: TaintResult,
        output_dir: Path,
    ) -> tuple[Path, Path]:
        """Write security_graph.json and taint_report.json."""
        # Security graph (annotated CPG)
        sg_path = output_dir / "security_graph.json"
        sg_data = self._cpg_to_dict(cpg)
        sg_path.write_text(json.dumps(sg_data, indent=2, default=str), encoding="utf-8")

        # Taint report
        report_path = output_dir / "taint_report.json"
        report: dict[str, Any] = {
            "job_id":               result.job_id,
            "cpg_job_id":           result.cpg_job_id,
            "summary": {
                "source_count":        result.source_count,
                "sink_count":          result.sink_count,
                "sanitizer_count":     result.sanitizer_count,
                "tainted_node_count":  result.tainted_node_count,
                "attack_path_count":   result.attack_path_count,
                "severity_breakdown":  result.severity_summary(),
            },
            "attack_paths": [p.to_dict() for p in paths],
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        report_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

        return sg_path, report_path

    def _cpg_to_dict(self, g: nx.DiGraph) -> dict[str, Any]:
        nodes = []
        for nid, attrs in g.nodes(data=True):
            node: dict[str, Any] = {"id": str(nid)}
            node.update(self._safe_attrs(attrs))
            nodes.append(node)
        edges = []
        for src, tgt, attrs in g.edges(data=True):
            edge: dict[str, Any] = {"source": str(src), "target": str(tgt)}
            edge.update(self._safe_attrs(attrs))
            edges.append(edge)
        return {"nodes": nodes, "edges": edges}

    def _safe_attrs(self, attrs: dict) -> dict:
        clean: dict[str, Any] = {}
        for k, v in attrs.items():
            if isinstance(v, (str, int, float, bool)) or v is None:
                clean[k] = v
            elif isinstance(v, (list, tuple)):
                clean[k] = list(v)
            elif isinstance(v, set):
                clean[k] = sorted(v)
            else:
                clean[k] = str(v)
        return clean

    def _count_sources_per_sink(
        self, paths: list[AttackPath]
    ) -> dict[str, int]:
        """Count how many distinct sources flow into each sink."""
        sink_sources: dict[str, set[str]] = {}
        for p in paths:
            sink_sources.setdefault(p.sink_node_id, set()).add(p.source_node_id)
        return {k: len(v) for k, v in sink_sources.items()}
