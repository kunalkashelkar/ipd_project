# ============================================================
# Taint Analysis — Result Model
# ============================================================

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from taint_analysis.models.path import AttackPath


@dataclass
class TaintResult:
    """Aggregated outcome of a complete taint analysis run."""

    job_id: str
    cpg_job_id: str                          # ParserJob that produced the CPG
    status: str = "completed"                # "completed" | "failed"

    # ── Detection counts ──────────────────────────────────
    source_count: int = 0
    sink_count: int = 0
    sanitizer_count: int = 0
    tainted_node_count: int = 0

    # ── Path severity breakdown ───────────────────────────
    attack_path_count: int = 0
    critical_path_count: int = 0
    high_path_count: int = 0
    medium_path_count: int = 0
    low_path_count: int = 0
    safe_path_count: int = 0

    # ── Output paths ─────────────────────────────────────
    security_graph_path: str = ""   # SA-CPG JSON with taint annotations
    taint_report_path: str = ""     # Full taint report JSON

    # ── Details ───────────────────────────────────────────
    attack_paths: list[AttackPath] = field(default_factory=list)
    error: str | None = None

    # ── Timing ────────────────────────────────────────────
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id":               self.job_id,
            "cpg_job_id":           self.cpg_job_id,
            "status":               self.status,
            "source_count":         self.source_count,
            "sink_count":           self.sink_count,
            "sanitizer_count":      self.sanitizer_count,
            "tainted_node_count":   self.tainted_node_count,
            "attack_path_count":    self.attack_path_count,
            "critical_path_count":  self.critical_path_count,
            "high_path_count":      self.high_path_count,
            "medium_path_count":    self.medium_path_count,
            "low_path_count":       self.low_path_count,
            "safe_path_count":      self.safe_path_count,
            "security_graph_path":  self.security_graph_path,
            "taint_report_path":    self.taint_report_path,
            "attack_paths":         [p.to_dict() for p in self.attack_paths],
            "error":                self.error,
            "started_at":           self.started_at.isoformat(),
            "completed_at":         self.completed_at.isoformat() if self.completed_at else None,
        }

    def severity_summary(self) -> dict[str, int]:
        return {
            "CRITICAL": self.critical_path_count,
            "HIGH":     self.high_path_count,
            "MEDIUM":   self.medium_path_count,
            "LOW":      self.low_path_count,
            "SAFE":     self.safe_path_count,
        }
