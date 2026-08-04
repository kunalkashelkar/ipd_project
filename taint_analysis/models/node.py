# ============================================================
# Taint Analysis — Node Model
# ============================================================

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TaintNode:
    """Security-enriched representation of a CPG node.

    These attributes are written back onto the NetworkX CPG node
    as additional attributes, forming the Security-Aware CPG (SA-CPG).
    """

    node_id: str
    label: str                        # Joern node type: CALL, IDENTIFIER, etc.
    code: str = ""                    # Source code snippet
    line_number: int | None = None
    filename: str | None = None

    # ── Security annotations ───────────────────────────────
    is_source: bool = False           # User-controlled input
    is_sink: bool = False             # Dangerous operation
    is_sanitized: bool = False        # Neutralises taint
    is_tainted: bool = False          # Receives tainted data

    # ── Taint tracking ─────────────────────────────────────
    taint_distance: int = -1          # BFS hops from nearest source; -1 = untainted
    taint_source_id: str | None = None  # ID of the source node that taints this node
    on_attack_path: bool = False      # True if this node is part of any attack path

    # ── Risk assessment ────────────────────────────────────
    risk_score: float = 0.0           # 0–10 composite score
    risk_level: str = "SAFE"          # SAFE | LOW | MEDIUM | HIGH | CRITICAL

    # ── Category metadata ──────────────────────────────────
    sink_category: str | None = None       # "buffer_overflow", "command_injection" …
    source_category: str | None = None     # "functions", "argv", "network" …

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id":         self.node_id,
            "label":           self.label,
            "code":            self.code,
            "line_number":     self.line_number,
            "filename":        self.filename,
            "is_source":       self.is_source,
            "is_sink":         self.is_sink,
            "is_sanitized":    self.is_sanitized,
            "is_tainted":      self.is_tainted,
            "taint_distance":  self.taint_distance,
            "taint_source_id": self.taint_source_id,
            "on_attack_path":  self.on_attack_path,
            "risk_score":      self.risk_score,
            "risk_level":      self.risk_level,
            "sink_category":   self.sink_category,
            "source_category": self.source_category,
        }

    @classmethod
    def from_cpg_node(cls, node_id: str, attrs: dict[str, Any]) -> "TaintNode":
        """Construct a TaintNode from a NetworkX CPG node attribute dict."""
        return cls(
            node_id=node_id,
            label=attrs.get("label", "UNKNOWN"),
            code=str(attrs.get("CODE") or attrs.get("code", "")),
            line_number=attrs.get("lineNumber") or attrs.get("line_number"),
            filename=attrs.get("filename") or attrs.get("FILENAME"),
        )
