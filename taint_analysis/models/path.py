# ============================================================
# Taint Analysis — Attack Path Model
# ============================================================

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AttackPath:
    """A complete taint flow from a source to a sink.

    Represents a concrete data-flow path that carries user-controlled
    (potentially malicious) input into a dangerous operation.
    """

    path_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_node_id: str = ""
    sink_node_id: str = ""

    # Ordered list of node IDs from source to sink (inclusive)
    nodes: list[str] = field(default_factory=list)

    # Ordered list of (source_id, target_id) edge tuples on this path
    edges: list[tuple[str, str]] = field(default_factory=list)

    length: int = 0                        # Number of hops (= len(nodes) - 1)
    sanitized: bool = False                # True if a sanitizer appears on the path
    sanitizer_node_ids: list[str] = field(default_factory=list)

    # Risk assessment
    severity: str = "UNKNOWN"             # CRITICAL | HIGH | MEDIUM | LOW | SAFE
    risk_score: float = 0.0               # 0–10

    # Context
    sink_category: str = ""              # "command_injection", "buffer_overflow" …
    source_category: str = ""            # "functions", "argv", "network" …
    source_code: str = ""
    sink_code: str = ""
    source_line: int | None = None
    sink_line: int | None = None
    filename: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "path_id":            self.path_id,
            "source_node_id":     self.source_node_id,
            "sink_node_id":       self.sink_node_id,
            "nodes":              self.nodes,
            "edges":              [{"source": s, "target": t} for s, t in self.edges],
            "length":             self.length,
            "sanitized":          self.sanitized,
            "sanitizer_node_ids": self.sanitizer_node_ids,
            "severity":           self.severity,
            "risk_score":         self.risk_score,
            "sink_category":      self.sink_category,
            "source_category":    self.source_category,
            "source_code":        self.source_code,
            "sink_code":          self.sink_code,
            "source_line":        self.source_line,
            "sink_line":          self.sink_line,
            "filename":           self.filename,
        }
