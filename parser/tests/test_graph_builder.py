# ============================================================
# Tests — Graph Builder
# ============================================================

from __future__ import annotations

import json
from pathlib import Path

import pytest

from parser.graph_builder.ast import ASTBuilder
from parser.graph_builder.cfg import CFGBuilder
from parser.graph_builder.cpg import CPGBuilder
from parser.graph_builder.dfg import DFGBuilder
from parser.graph_builder.serializer import GraphSerializer
from parser.graph_builder.validator import GraphValidator, Severity
from parser.joern.importer import GraphSONImporter, RawGraph

FIXTURE = Path(__file__).parent / "fixtures" / "sample_graphson.json"


@pytest.fixture
def raw_graph() -> RawGraph:
    importer = GraphSONImporter()
    return importer.load(FIXTURE.parent)


# ── Importer ───────────────────────────────────────────────

class TestGraphSONImporter:

    def test_loads_vertices(self, raw_graph: RawGraph) -> None:
        assert raw_graph.vertex_count == 6

    def test_loads_edges(self, raw_graph: RawGraph) -> None:
        assert raw_graph.edge_count == 8

    def test_raises_on_empty_dir(self, tmp_path: Path) -> None:
        from parser.joern.importer import GraphSONImportError
        (tmp_path / "placeholder").mkdir()
        with pytest.raises(GraphSONImportError):
            GraphSONImporter().load(tmp_path / "placeholder")


# ── AST Builder ────────────────────────────────────────────

class TestASTBuilder:

    def test_builds_ast(self, raw_graph: RawGraph) -> None:
        ast = ASTBuilder().build(raw_graph)
        assert ast.number_of_nodes() > 0

    def test_only_ast_edges(self, raw_graph: RawGraph) -> None:
        ast = ASTBuilder().build(raw_graph)
        for _, _, data in ast.edges(data=True):
            assert data.get("label") == "AST"

    def test_finds_method_node(self, raw_graph: RawGraph) -> None:
        ast = ASTBuilder().build(raw_graph)
        fns = ASTBuilder().get_functions(ast)
        assert len(fns) >= 1
        assert fns[0]["label"] == "METHOD"


# ── CFG Builder ────────────────────────────────────────────

class TestCFGBuilder:

    def test_builds_cfg(self, raw_graph: RawGraph) -> None:
        cfg = CFGBuilder().build(raw_graph)
        assert cfg.number_of_nodes() > 0

    def test_only_cfg_edges(self, raw_graph: RawGraph) -> None:
        cfg = CFGBuilder().build(raw_graph)
        for _, _, data in cfg.edges(data=True):
            assert data.get("label") == "CFG"

    def test_entry_nodes(self, raw_graph: RawGraph) -> None:
        cfg = CFGBuilder().build(raw_graph)
        entries = CFGBuilder().get_entry_nodes(cfg)
        assert len(entries) >= 1


# ── DFG Builder ────────────────────────────────────────────

class TestDFGBuilder:

    def test_builds_dfg(self, raw_graph: RawGraph) -> None:
        dfg = DFGBuilder().build(raw_graph)
        assert dfg.number_of_edges() >= 1

    def test_variable_attribute_on_edges(self, raw_graph: RawGraph) -> None:
        dfg = DFGBuilder().build(raw_graph)
        for _, _, data in dfg.edges(data=True):
            assert "variable" in data

    def test_finds_definitions(self, raw_graph: RawGraph) -> None:
        dfg = DFGBuilder().build(raw_graph)
        defs = DFGBuilder().get_definitions(dfg)
        assert len(defs) >= 1


# ── CPG Builder ────────────────────────────────────────────

class TestCPGBuilder:

    def test_merge_contains_all_nodes(self, raw_graph: RawGraph) -> None:
        builder = CPGBuilder()
        cpg, ast, cfg, dfg = builder.build_from_raw(raw_graph)
        # CPG must have at least as many nodes as the largest individual graph
        max_individual = max(ast.number_of_nodes(), cfg.number_of_nodes(), dfg.number_of_nodes())
        assert cpg.number_of_nodes() >= max_individual

    def test_layers_attribute_on_nodes(self, raw_graph: RawGraph) -> None:
        cpg, *_ = CPGBuilder().build_from_raw(raw_graph)
        for _, data in cpg.nodes(data=True):
            assert "_layers" in data
            assert isinstance(data["_layers"], list)

    def test_serializer_produces_valid_json(self, raw_graph: RawGraph) -> None:
        cpg, ast, cfg, dfg = CPGBuilder().build_from_raw(raw_graph)
        d = GraphSerializer().to_dict(cpg)
        # Must be JSON-serialisable
        encoded = json.dumps(d)
        decoded = json.loads(encoded)
        assert "nodes" in decoded and "edges" in decoded

    def test_statistics_keys(self, raw_graph: RawGraph) -> None:
        cpg, ast, cfg, dfg = CPGBuilder().build_from_raw(raw_graph)
        stats = GraphSerializer().statistics(cpg, ast, cfg, dfg)
        for key in ("total_nodes", "total_edges", "ast_nodes", "cfg_nodes", "dfg_nodes", "function_count"):
            assert key in stats


# ── Graph Validator ────────────────────────────────────────

class TestGraphValidator:

    def test_valid_graph_passes(self, raw_graph: RawGraph) -> None:
        cpg, *_ = CPGBuilder().build_from_raw(raw_graph)
        report = GraphValidator().validate(cpg)
        assert not report.has_errors

    def test_empty_graph_fails(self) -> None:
        import networkx as nx
        empty = nx.DiGraph()
        report = GraphValidator().validate(empty)
        assert report.has_errors
        assert "EMPTY_GRAPH" in report.error_codes

    def test_no_method_node_fails(self) -> None:
        import networkx as nx
        g = nx.DiGraph()
        g.add_node("1", label="CALL", _layers=["AST"])
        g.add_node("2", label="IDENTIFIER", _layers=["AST"])
        g.add_edge("1", "2", label="AST")
        report = GraphValidator().validate(g)
        assert report.has_errors
        assert "NO_METHOD_NODES" in report.error_codes
