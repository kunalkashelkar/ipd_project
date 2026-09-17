# ============================================================
# Static Analysis Service (Phase 4 Canonical Graph Pipeline)
# ============================================================

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import networkx as nx
from loguru import logger

from backend.app.core.config import get_settings
from backend.app.services.static_analysis.process_runner import (
    AnalysisProcessRunner,
    ProcessExecutionError,
    ProcessTimeoutError,
)
from parser.graph_builder.cpg import CPGBuilder
from parser.graph_builder.serializer import GraphSerializer
from parser.graph_builder.validator import GraphValidator
from parser.joern.config import get_joern_config
from parser.joern.importer import GraphSONImporter, RawGraph


@dataclass
class GeneratedArtifactMeta:
    """Metadata describing a generated canonical graph artifact."""

    artifact_id: uuid.UUID
    artifact_type: str
    schema_version: str
    artifact_path: Path
    content_hash: str
    size_bytes: int
    node_count: int
    edge_count: int
    tool_name: str
    tool_version: str
    status: str = "ready"
    metadata: dict[str, Any] = field(default_factory=dict)
    error_message: str | None = None


class StaticAnalysisService:
    """Orchestrates static analysis, Joern invocation, canonical graph generation, and artifact serialization.

    Produces canonical AST, CFG, PDG, CPG, and Call Graph representations
    bound to the immutable SourceSnapshot provenance contract.
    """

    SCHEMA_VERSION = "1.0.0"

    def __init__(self) -> None:
        self.settings = get_settings()
        self.joern_cfg = get_joern_config()
        self.runner = AnalysisProcessRunner()
        self.importer = GraphSONImporter()
        self.cpg_builder = CPGBuilder()
        self.serializer = GraphSerializer()
        self.validator = GraphValidator()

    def analyze(
        self,
        *,
        source_dir: Path,
        workspace: Path,
        scan_id: uuid.UUID,
        snapshot_id: uuid.UUID,
        config: dict[str, Any] | None = None,
    ) -> tuple[dict[str, GeneratedArtifactMeta], nx.DiGraph]:
        """Execute static analysis pipeline and produce canonical graph artifacts.

        Returns:
            Tuple of (artifacts_dict, merged_cpg_networkx_graph).
        """
        workspace.mkdir(parents=True, exist_ok=True)
        config = config or {}

        # 1. Determine analysis strategy: Joern CLI vs Native Language Analyzers
        has_joern = self._is_joern_available()
        c_files = list(source_dir.rglob("*.c")) + list(source_dir.rglob("*.cpp")) + list(source_dir.rglob("*.h"))
        tool_name = "joern" if (has_joern and len(c_files) > 0) else "native_ast_analyzer"
        tool_version = "2.0.400" if tool_name == "joern" else "1.0.0"

        logger.info(
            "Static analysis running for scan {scan_id} using engine '{tool}' (c_files={c})",
            scan_id=scan_id,
            tool=tool_name,
            c=len(c_files),
        )

        cpg: nx.DiGraph
        ast_graph: nx.DiGraph
        cfg_graph: nx.DiGraph
        pdg_graph: nx.DiGraph
        call_graph: nx.DiGraph

        if tool_name == "joern":
            cpg, ast_graph, cfg_graph, pdg_graph = self._run_joern_pipeline(source_dir, workspace)
            call_graph = self._extract_call_graph_from_cpg(cpg)
        else:
            ast_graph, cfg_graph, pdg_graph, cpg, call_graph = self._run_native_multilang_pipeline(source_dir)

        # 2. Serialize canonical artifacts complying with Schema v1.0.0
        artifacts: dict[str, GeneratedArtifactMeta] = {}
        graphs = {
            "AST": ast_graph,
            "CFG": cfg_graph,
            "PDG": pdg_graph,
            "CPG": cpg,
            "CALL_GRAPH": call_graph,
        }

        for graph_type, g in graphs.items():
            meta = self._serialize_and_save_artifact(
                graph=g,
                graph_type=graph_type,
                workspace=workspace,
                scan_id=scan_id,
                snapshot_id=snapshot_id,
                tool_name=tool_name,
                tool_version=tool_version,
            )
            artifacts[graph_type] = meta

        return artifacts, cpg

    # ── Joern Execution ────────────────────────────────────

    def _is_joern_available(self) -> bool:
        """Check if Joern CLI parse and export binaries exist and are executable."""
        try:
            return self.joern_cfg.is_joern_available()
        except Exception:
            return False

    def _run_joern_pipeline(
        self, source_dir: Path, workspace: Path
    ) -> tuple[nx.DiGraph, nx.DiGraph, nx.DiGraph, nx.DiGraph]:
        """Execute joern-parse and joern-export via AnalysisProcessRunner."""
        cpg_bin = workspace / "cpg.bin"
        export_dir = workspace / "graphson"
        export_dir.mkdir(parents=True, exist_ok=True)

        parse_cmd = [
            self.joern_cfg.parse_bin,
            source_dir,
            "-o",
            cpg_bin,
        ]
        self.runner.run(
            parse_cmd,
            timeout=self.joern_cfg.joern_timeout,
            label="joern-parse",
        )

        export_cmd = [
            self.joern_cfg.export_bin,
            cpg_bin,
            "--repr",
            "all",
            "--format",
            "graphson",
            "--out",
            export_dir,
        ]
        self.runner.run(
            export_cmd,
            timeout=self.joern_cfg.joern_timeout,
            label="joern-export",
        )

        raw = self.importer.load(export_dir)
        return self.cpg_builder.build_from_raw(raw)

    # ── Native Multi-Language Pipeline ─────────────────────

    def _run_native_multilang_pipeline(
        self, source_dir: Path
    ) -> tuple[nx.DiGraph, nx.DiGraph, nx.DiGraph, nx.DiGraph, nx.DiGraph]:
        """Construct deterministic AST, CFG, PDG, CPG, and CallGraph from source files."""
        ast_g = nx.DiGraph()
        cfg_g = nx.DiGraph()
        pdg_g = nx.DiGraph()
        call_g = nx.DiGraph()

        node_id_counter = 0

        # Scan all text code files
        valid_exts = {".py", ".js", ".ts", ".c", ".cpp", ".h", ".json", ".yaml", ".yml"}
        files = [p for p in source_dir.rglob("*") if p.is_file() and p.suffix.lower() in valid_exts]

        for file_path in files:
            rel_path = str(file_path.relative_to(source_dir)).replace("\\", "/")
            try:
                content = file_path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            file_node_id = f"file_{rel_path}"
            ast_g.add_node(file_node_id, label="SOURCE_FILE", path=rel_path, _layers=["AST"])
            cfg_g.add_node(file_node_id, label="SOURCE_FILE", path=rel_path, _layers=["CFG"])
            call_g.add_node(file_node_id, label="SOURCE_FILE", path=rel_path, _layers=["CALL_GRAPH"])

            if file_path.suffix.lower() == ".py":
                self._parse_python_file(content, rel_path, ast_g, cfg_g, pdg_g, call_g)
            else:
                self._parse_generic_source_file(content, rel_path, ast_g, cfg_g, pdg_g, call_g)

        # Merge AST, CFG, PDG into unified CPG
        cpg = self.cpg_builder.merge(ast_g, cfg_g, pdg_g)
        return ast_g, cfg_g, pdg_g, cpg, call_g

    def _parse_python_file(
        self, content: str, rel_path: str, ast_g: nx.DiGraph, cfg_g: nx.DiGraph, pdg_g: nx.DiGraph, call_g: nx.DiGraph
    ) -> None:
        """Extract nodes & edges for Python files using Python AST."""
        try:
            tree = ast.parse(content)
        except Exception:
            self._parse_generic_source_file(content, rel_path, ast_g, cfg_g, pdg_g, call_g)
            return

        def visit_node(node: ast.AST, parent_id: str | None = None) -> str:
            node_id = f"{rel_path}:{node.__class__.__name__}_{id(node)}"
            label = node.__class__.__name__
            lineno = getattr(node, "lineno", 1)
            col_offset = getattr(node, "col_offset", 0)

            props = {
                "label": label,
                "path": rel_path,
                "line": lineno,
                "col": col_offset,
                "_layers": ["AST"],
            }

            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                props["name"] = node.name
                props["label"] = "METHOD"
                func_node_id = f"{rel_path}::{node.name}"
                call_g.add_node(func_node_id, label="METHOD", name=node.name, path=rel_path, line=lineno)

            if isinstance(node, ast.Name):
                props["name"] = node.id
            elif isinstance(node, ast.Constant):
                props["value"] = str(node.value)

            ast_g.add_node(node_id, **props)
            if parent_id:
                ast_g.add_edge(parent_id, node_id, label="AST", layer="AST")

            # Simple statement sequential CFG / PDG
            if isinstance(node, (ast.stmt, ast.expr)):
                cfg_g.add_node(node_id, **props)
                if parent_id and cfg_g.has_node(parent_id):
                    cfg_g.add_edge(parent_id, node_id, label="CFG", layer="CFG")
                pdg_g.add_node(node_id, **props)

            # Call Graph
            if isinstance(node, ast.Call):
                call_name = ""
                if isinstance(node.func, ast.Name):
                    call_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    call_name = node.func.attr
                if call_name:
                    call_id = f"{rel_path}:call:{call_name}:{lineno}"
                    call_g.add_node(call_id, label="CALL", name=call_name, path=rel_path, line=lineno)
                    if parent_id:
                        call_g.add_edge(parent_id, call_id, label="CALLS")

            for child in ast.iter_child_nodes(node):
                visit_node(child, node_id)

            return node_id

        visit_node(tree, f"file_{rel_path}")

    def _parse_generic_source_file(
        self, content: str, rel_path: str, ast_g: nx.DiGraph, cfg_g: nx.DiGraph, pdg_g: nx.DiGraph, call_g: nx.DiGraph
    ) -> None:
        """Deterministic regex-based statement & function parser for JS/TS/C/C++."""
        lines = content.splitlines()
        file_node_id = f"file_{rel_path}"
        prev_stmt_id = file_node_id

        for idx, line in enumerate(lines, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith(("//", "/*", "*", "#")):
                continue

            stmt_id = f"{rel_path}:line_{idx}"
            props = {
                "label": "STATEMENT",
                "code": stripped[:100],
                "path": rel_path,
                "line": idx,
                "_layers": ["AST", "CFG"],
            }

            ast_g.add_node(stmt_id, **props)
            ast_g.add_edge(file_node_id, stmt_id, label="AST", layer="AST")

            cfg_g.add_node(stmt_id, **props)
            if prev_stmt_id:
                cfg_g.add_edge(prev_stmt_id, stmt_id, label="CFG", layer="CFG")
            prev_stmt_id = stmt_id

            # Detect function definitions & calls
            func_match = re.search(r"\b(?:function\s+([A-Za-z0-9_$]+)|([A-Za-z0-9_$]+)\s*\([^)]*\)\s*\{)", stripped)
            if func_match:
                fname = func_match.group(1) or func_match.group(2)
                fnode_id = f"{rel_path}::{fname}"
                call_g.add_node(fnode_id, label="METHOD", name=fname, path=rel_path, line=idx)
                call_g.add_edge(file_node_id, fnode_id, label="CONTAINS")

            call_match = re.findall(r"\b([A-Za-z0-9_$]+)\s*\(", stripped)
            for call_name in call_match:
                if call_name not in {"function", "if", "for", "while", "switch", "catch"}:
                    cid = f"{rel_path}:call:{call_name}_{idx}"
                    call_g.add_node(cid, label="CALL", name=call_name, path=rel_path, line=idx)
                    call_g.add_edge(prev_stmt_id, cid, label="CALLS")

    def _extract_call_graph_from_cpg(self, cpg: nx.DiGraph) -> nx.DiGraph:
        """Derive CallGraph subgraph from a Joern CPG."""
        call_g = nx.DiGraph()
        for nid, data in cpg.nodes(data=True):
            lbl = data.get("label", "")
            if lbl in {"METHOD", "CALL"}:
                call_g.add_node(nid, **data)
        for u, v, data in cpg.edges(data=True):
            if data.get("label") == "CALL" or (call_g.has_node(u) and call_g.has_node(v)):
                call_g.add_edge(u, v, **data)
        return call_g

    # ── Artifact Serialization & Checksum ──────────────────

    def _serialize_and_save_artifact(
        self,
        *,
        graph: nx.DiGraph,
        graph_type: str,
        workspace: Path,
        scan_id: uuid.UUID,
        snapshot_id: uuid.UUID,
        tool_name: str,
        tool_version: str,
    ) -> GeneratedArtifactMeta:
        """Write canonical graph JSON file, compute SHA-256 hash, and return metadata."""
        artifact_id = uuid.uuid4()
        artifact_file = workspace / f"{graph_type.lower()}_{artifact_id}.json"

        nodes = []
        for nid, attrs in graph.nodes(data=True):
            node_dict = {"id": str(nid)}
            for k, v in attrs.items():
                if isinstance(v, (str, int, float, bool)) or v is None:
                    node_dict[k] = v
                elif isinstance(v, (list, tuple, set)):
                    node_dict[k] = list(v)
                else:
                    node_dict[k] = str(v)
            nodes.append(node_dict)

        edges = []
        for u, v, attrs in graph.edges(data=True):
            edge_dict = {"source": str(u), "target": str(v)}
            for k, v in attrs.items():
                if isinstance(v, (str, int, float, bool)) or v is None:
                    edge_dict[k] = v
                elif isinstance(v, (list, tuple, set)):
                    edge_dict[k] = list(v)
                else:
                    edge_dict[k] = str(v)
            edges.append(edge_dict)

        canonical_data = {
            "schema_version": self.SCHEMA_VERSION,
            "artifact_id": str(artifact_id),
            "scan_id": str(scan_id),
            "source_snapshot_id": str(snapshot_id),
            "graph_type": graph_type,
            "tool_name": tool_name,
            "tool_version": tool_version,
            "node_count": len(nodes),
            "edge_count": len(edges),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "nodes": nodes,
            "edges": edges,
        }

        json_bytes = json.dumps(canonical_data, indent=2).encode("utf-8")
        artifact_file.write_bytes(json_bytes)

        sha256_hash = hashlib.sha256(json_bytes).hexdigest()

        # Determine truthful artifact status and capability metadata
        status = "ready"
        metadata: dict[str, Any] = {"node_count": len(nodes), "edge_count": len(edges)}
        if graph_type == "PDG" and (tool_name == "native_ast_analyzer" or len(edges) == 0):
            status = "unsupported"
            metadata["note"] = (
                "Program Dependence Graph (PDG) data/control dependency edges require "
                "the Joern static analysis engine; not supported by native AST parser fallback."
            )
            metadata["engine_fallback"] = True

        return GeneratedArtifactMeta(
            artifact_id=artifact_id,
            artifact_type=graph_type,
            schema_version=self.SCHEMA_VERSION,
            artifact_path=artifact_file,
            content_hash=sha256_hash,
            size_bytes=len(json_bytes),
            node_count=len(nodes),
            edge_count=len(edges),
            tool_name=tool_name,
            tool_version=tool_version,
            status=status,
            metadata=metadata,
        )

