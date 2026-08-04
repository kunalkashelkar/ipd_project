# ============================================================
# Graph Builder — Code Property Graph (CPG) Merger
# ============================================================
# Merges the AST, CFG, and DFG subgraphs into a single unified
# directed multigraph. Nodes are shared across layers; edges
# carry a 'layer' attribute to identify their origin.
# ============================================================

from __future__ import annotations

import networkx as nx
from loguru import logger

from parser.joern.importer import RawGraph


class CPGBuilder:
    """Merges AST, CFG, and DFG into a single Code Property Graph."""

    def merge(
        self,
        ast: nx.DiGraph,
        cfg: nx.DiGraph,
        dfg: nx.DiGraph,
    ) -> nx.DiGraph:
        """Combine three layered graphs into one unified CPG.

        Strategy:
        - All nodes from AST, CFG, DFG are added to the CPG.
        - When the same node ID appears in multiple layers,
          the richest set of properties is kept (later layers can
          add attributes but not overwrite existing ones).
        - Edges from each layer are added with their original label
          plus a ``layer`` attribute.

        Args:
            ast: AST subgraph produced by :class:`ASTBuilder`.
            cfg: CFG subgraph produced by :class:`CFGBuilder`.
            dfg: DFG subgraph produced by :class:`DFGBuilder`.

        Returns:
            A unified NetworkX DiGraph (not MultiDiGraph — parallel
            edges may be collapsed but layer info is preserved on attrs).
        """
        cpg = nx.DiGraph()

        # Add nodes from each layer (AST first, then enrich with CFG/DFG attributes)
        for source_graph, layer_name in [(ast, "AST"), (cfg, "CFG"), (dfg, "DFG")]:
            for node_id, attrs in source_graph.nodes(data=True):
                if cpg.has_node(node_id):
                    # Enrich existing node — do not overwrite already-set attrs
                    existing = cpg.nodes[node_id]
                    for k, v in attrs.items():
                        if k not in existing:
                            existing[k] = v
                    # Track which layers contain this node
                    existing.setdefault("_layers", set()).add(layer_name)
                else:
                    node_data = dict(attrs)
                    node_data["_layers"] = {layer_name}
                    cpg.add_node(node_id, **node_data)

        # Add edges from each layer
        for source_graph, layer_name in [(ast, "AST"), (cfg, "CFG"), (dfg, "DFG")]:
            for src, tgt, attrs in source_graph.edges(data=True):
                edge_data = dict(attrs)
                edge_data["layer"] = layer_name
                # If edge already exists (same src→tgt), keep the first one
                # but append the layer to a 'layers' list attribute
                if cpg.has_edge(src, tgt):
                    existing_edge = cpg[src][tgt]
                    existing_edge.setdefault("_layers", set()).add(layer_name)
                else:
                    edge_data["_layers"] = {layer_name}
                    cpg.add_edge(src, tgt, **edge_data)

        # Convert sets to sorted lists for JSON serialisability
        for _, attrs in cpg.nodes(data=True):
            if "_layers" in attrs:
                attrs["_layers"] = sorted(attrs["_layers"])
        for _, _, attrs in cpg.edges(data=True):
            if "_layers" in attrs:
                attrs["_layers"] = sorted(attrs["_layers"])

        logger.info(
            "CPG merged — nodes={n} edges={e} (ast={a} cfg={c} dfg={d})",
            n=cpg.number_of_nodes(),
            e=cpg.number_of_edges(),
            a=ast.number_of_nodes(),
            c=cfg.number_of_nodes(),
            d=dfg.number_of_nodes(),
        )
        return cpg

    def build_from_raw(self, raw: RawGraph) -> "tuple[nx.DiGraph, nx.DiGraph, nx.DiGraph, nx.DiGraph]":
        """Convenience method: build all layers and merge.

        Returns:
            (cpg, ast, cfg, dfg) — all four graphs.
        """
        from parser.graph_builder.ast import ASTBuilder
        from parser.graph_builder.cfg import CFGBuilder
        from parser.graph_builder.dfg import DFGBuilder

        ast = ASTBuilder().build(raw)
        cfg = CFGBuilder().build(raw)
        dfg = DFGBuilder().build(raw)
        cpg = self.merge(ast, cfg, dfg)
        return cpg, ast, cfg, dfg
