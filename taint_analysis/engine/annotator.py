# ============================================================
# Taint Engine — Graph Annotator
# ============================================================
# Writes all taint analysis results back onto the CPG's node
# and edge attributes, producing the Security-Aware CPG (SA-CPG).
# ============================================================

from __future__ import annotations

import networkx as nx
from loguru import logger

from taint_analysis.engine.propagation import TaintInfo
from taint_analysis.models.path import AttackPath

# Taint annotation defaults for every node (ensures the GNN always sees
# these feature keys, even for untainted nodes)
_DEFAULT_TAINT_ATTRS: dict = {
    "is_source":       False,
    "is_sink":         False,
    "is_sanitized":    False,
    "is_tainted":      False,
    "on_attack_path":  False,
    "taint_distance":  -1,
    "taint_source_id": None,
    "risk_score":      0.0,
    "risk_level":      "SAFE",
    "sink_category":   None,
    "source_category": None,
}


class GraphAnnotator:
    """Writes taint metadata onto the CPG DiGraph in-place.

    After annotation, every node has the full set of taint feature
    keys (see ``_DEFAULT_TAINT_ATTRS``), making the graph ready
    for feature engineering in Phase 4.
    """

    def annotate(
        self,
        cpg: nx.DiGraph,
        taint: dict[str, TaintInfo],
        attack_paths: list[AttackPath],
        path_risk_scores: dict[str, tuple[float, str]],  # path_id → (score, level)
    ) -> nx.DiGraph:
        """Annotate *cpg* with all taint analysis results.

        Args:
            cpg:              The merged CPG to annotate (mutated in-place).
            taint:            TaintInfo mapping from propagation step.
            attack_paths:     Extracted attack paths.
            path_risk_scores: Risk score per path_id from RiskScorer.

        Returns:
            The same *cpg* with taint attributes written on every node and edge.
        """
        # ── Step 1: Set defaults on all nodes ──────────────
        for node_id in cpg.nodes:
            attrs = cpg.nodes[node_id]
            for key, default in _DEFAULT_TAINT_ATTRS.items():
                attrs.setdefault(key, default)

        # ── Step 2: Write TaintInfo onto each tainted node ─
        for node_id, info in taint.items():
            if not cpg.has_node(node_id):
                continue
            attrs = cpg.nodes[node_id]
            if info.is_tainted:
                attrs["is_tainted"]      = True
                attrs["taint_distance"]  = info.taint_distance
                attrs["taint_source_id"] = info.taint_source_id

        # ── Step 3: Mark attack path nodes ─────────────────
        attack_path_node_set: set[str] = set()
        attack_path_edge_set: set[tuple[str, str]] = set()

        for path in attack_paths:
            score, level = path_risk_scores.get(path.path_id, (path.risk_score, path.severity))
            # Propagate score + level back onto the path object
            path.risk_score = score
            path.severity   = level

            for nid in path.nodes:
                attack_path_node_set.add(nid)
            for src, tgt in path.edges:
                attack_path_edge_set.add((src, tgt))

        for node_id in attack_path_node_set:
            if cpg.has_node(node_id):
                cpg.nodes[node_id]["on_attack_path"] = True

        # ── Step 4: Mark attack path edges ─────────────────
        for src, tgt in attack_path_edge_set:
            if cpg.has_edge(src, tgt):
                cpg[src][tgt]["on_attack_path"] = True
            else:
                cpg[src][tgt].setdefault("on_attack_path", False)

        # ── Step 5: Set node risk scores ───────────────────
        # A node's risk score = max score across all paths it appears on
        node_max_score: dict[str, float] = {}
        node_max_level: dict[str, str]   = {}
        for path in attack_paths:
            for nid in path.nodes:
                cur = node_max_score.get(nid, -1.0)
                if path.risk_score > cur:
                    node_max_score[nid] = path.risk_score
                    node_max_level[nid] = path.severity

        for node_id, score in node_max_score.items():
            if cpg.has_node(node_id):
                cpg.nodes[node_id]["risk_score"] = score
                cpg.nodes[node_id]["risk_level"] = node_max_level[node_id]

        # ── Default edge annotation ────────────────────────
        for _, _, eattrs in cpg.edges(data=True):
            eattrs.setdefault("on_attack_path", False)

        annotated = sum(1 for _, d in cpg.nodes(data=True) if d.get("is_tainted"))
        logger.info(
            "CPG annotated — tainted nodes={t} attack path nodes={a}",
            t=annotated,
            a=len(attack_path_node_set),
        )
        return cpg
