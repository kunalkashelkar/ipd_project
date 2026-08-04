# ============================================================
# Taint Engine — BFS Taint Propagation
# ============================================================
# Forward BFS over DFG (REACHING_DEF) edges starting from all
# source nodes simultaneously. Sanitizer nodes block propagation
# for their downstream successors.
#
# Design: intra-procedural, forward-only.
# ============================================================

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any

import networkx as nx
from loguru import logger

# Edge labels that carry data-flow (REACHING_DEF is Joern's primary DFG label)
_DFG_EDGE_LABELS = frozenset({"DFG", "REACHING_DEF", "REACHING_DEF_EDGE"})

# Edge labels that represent assignments / parameter passing (also propagate taint)
_PROPAGATING_EDGE_LABELS = _DFG_EDGE_LABELS | frozenset({
    "ARGUMENT",    # argument passed to a function call
    "RECEIVER",    # receiver object in OOP calls
    "CALL",        # direct call edge (arg → param)
})


@dataclass
class TaintInfo:
    """Per-node taint metadata produced by propagation BFS."""
    node_id: str
    is_tainted: bool = False
    taint_distance: int = -1        # hops from nearest source (-1 = untainted)
    taint_source_id: str | None = None
    blocked_by: str | None = None   # sanitizer node_id that blocked further propagation


class TaintPropagator:
    """Forward BFS taint propagation over DFG edges.

    Algorithm:
        1. Enqueue all source nodes (distance = 0, tainted = True).
        2. For each dequeued node:
           a. Mark it as tainted with the current distance.
           b. For each outgoing DFG/propagating edge:
              - If successor is a sanitizer → mark its TaintInfo as blocked;
                do NOT enqueue the sanitizer's successors.
              - If successor not yet visited (or reachable at a shorter distance)
                → enqueue with distance + 1.
        3. Return the complete TaintInfo dict for all visited nodes.
    """

    def propagate(
        self,
        cpg: nx.DiGraph,
        source_ids: list[str],
        sanitizer_ids: set[str],
    ) -> dict[str, TaintInfo]:
        """Run taint propagation from *source_ids*.

        Args:
            cpg:           The merged CPG NetworkX DiGraph.
            source_ids:    List of source node IDs (seeds).
            sanitizer_ids: Set of sanitizer node IDs (block propagation).

        Returns:
            Mapping of node_id → :class:`TaintInfo` for every tainted node.
        """
        taint: dict[str, TaintInfo] = {}

        # Pre-mark all sanitizers in the result dict (but NOT as tainted)
        for san_id in sanitizer_ids:
            taint[san_id] = TaintInfo(node_id=san_id, is_tainted=False, taint_distance=-1)

        # BFS queue: (node_id, distance, originating_source_id)
        queue: deque[tuple[str, int, str]] = deque()

        for src_id in source_ids:
            if not cpg.has_node(src_id):
                continue
            taint[src_id] = TaintInfo(
                node_id=src_id,
                is_tainted=True,
                taint_distance=0,
                taint_source_id=src_id,
            )
            queue.append((src_id, 0, src_id))

        visited_at: dict[str, int] = {src: 0 for src in source_ids}

        while queue:
            current_id, dist, origin_src = queue.popleft()

            for _, successor_id, edge_attrs in cpg.out_edges(current_id, data=True):
                edge_label = edge_attrs.get("label", "")
                original_label = edge_attrs.get("original_label", edge_label)

                # Only propagate along data-flow edges
                if (edge_label not in _PROPAGATING_EDGE_LABELS and
                        original_label not in _PROPAGATING_EDGE_LABELS):
                    continue

                new_dist = dist + 1

                # ── Sanitizer: mark blocked, do NOT propagate further ──
                if successor_id in sanitizer_ids:
                    existing = taint.get(successor_id)
                    if existing is None:
                        taint[successor_id] = TaintInfo(
                            node_id=successor_id,
                            is_tainted=False,
                            taint_distance=-1,
                            blocked_by=origin_src,
                        )
                    else:
                        existing.blocked_by = origin_src
                    continue

                # ── Already visited at a shorter or equal distance → skip ──
                prev_dist = visited_at.get(successor_id, -1)
                if prev_dist != -1 and prev_dist <= new_dist:
                    continue

                # ── Mark as tainted and enqueue ──
                visited_at[successor_id] = new_dist
                taint[successor_id] = TaintInfo(
                    node_id=successor_id,
                    is_tainted=True,
                    taint_distance=new_dist,
                    taint_source_id=origin_src,
                )
                queue.append((successor_id, new_dist, origin_src))

        tainted_count = sum(1 for t in taint.values() if t.is_tainted)
        logger.info(
            "Taint propagation — tainted={t} total_visited={v}",
            t=tainted_count,
            v=len(taint),
        )
        return taint

    def get_tainted_subgraph(
        self,
        cpg: nx.DiGraph,
        taint: dict[str, TaintInfo],
    ) -> nx.DiGraph:
        """Return a CPG subgraph containing only tainted nodes and their DFG edges.

        This is used by the attack path extractor for efficient traversal.
        """
        tainted_nodes = {nid for nid, info in taint.items() if info.is_tainted}
        sub = cpg.subgraph(tainted_nodes).copy()
        # Remove non-DFG edges to keep only flow edges
        edges_to_remove = [
            (u, v) for u, v, d in sub.edges(data=True)
            if d.get("label") not in _PROPAGATING_EDGE_LABELS
            and d.get("original_label") not in _PROPAGATING_EDGE_LABELS
        ]
        sub.remove_edges_from(edges_to_remove)
        return sub
