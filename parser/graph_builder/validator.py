# ============================================================
# Graph Builder — Graph Integrity Validator
# ============================================================
# Checks the merged CPG for structural correctness before
# storage and downstream use.
# ============================================================

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

import networkx as nx
from loguru import logger


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class Issue:
    severity: Severity
    code: str
    message: str


@dataclass
class ValidationReport:
    issues: list[Issue] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(i.severity == Severity.ERROR for i in self.issues)

    @property
    def error_codes(self) -> list[str]:
        return [i.code for i in self.issues if i.severity == Severity.ERROR]

    def to_dict(self) -> dict:
        return {
            "valid": not self.has_errors,
            "issues": [
                {"severity": i.severity.value, "code": i.code, "message": i.message}
                for i in self.issues
            ],
        }


class GraphValidator:
    """Validates a merged CPG for structural correctness."""

    def validate(self, cpg: nx.DiGraph) -> ValidationReport:
        """Run all checks and return a :class:`ValidationReport`.

        Args:
            cpg: The merged CPG to validate.

        Returns:
            A ValidationReport. Call ``.has_errors`` to decide whether
            to abort the pipeline.
        """
        report = ValidationReport()

        self._check_empty(cpg, report)
        self._check_method_nodes(cpg, report)
        self._check_duplicate_nodes(cpg, report)
        self._check_orphan_nodes(cpg, report)
        self._check_self_loops(cpg, report)

        status = "INVALID" if report.has_errors else "VALID"
        logger.info(
            "Graph validation {status} — issues={n}",
            status=status,
            n=len(report.issues),
        )
        return report

    # ── Checks ─────────────────────────────────────────────

    def _check_empty(self, g: nx.DiGraph, r: ValidationReport) -> None:
        if g.number_of_nodes() == 0:
            r.issues.append(Issue(
                Severity.ERROR, "EMPTY_GRAPH",
                "CPG contains zero nodes. Parsing may have failed silently.",
            ))

    def _check_method_nodes(self, g: nx.DiGraph, r: ValidationReport) -> None:
        methods = [n for n, d in g.nodes(data=True) if d.get("label") == "METHOD"]
        if not methods:
            r.issues.append(Issue(
                Severity.ERROR, "NO_METHOD_NODES",
                "CPG contains no METHOD nodes. The source file may be empty or Joern failed to parse it.",
            ))
        else:
            r.issues.append(Issue(
                Severity.INFO, "METHOD_COUNT",
                f"Found {len(methods)} METHOD node(s).",
            ))

    def _check_duplicate_nodes(self, g: nx.DiGraph, r: ValidationReport) -> None:
        # NetworkX DiGraph deduplicates by node ID automatically; this checks for
        # nodes with identical (label, line_number, file) tuples which could indicate
        # a CPG merge bug.
        seen: set[tuple] = set()
        dups = 0
        for _, data in g.nodes(data=True):
            key = (data.get("label"), data.get("lineNumber"), data.get("filename"))
            if key in seen and key != (None, None, None):
                dups += 1
            seen.add(key)
        if dups > 0:
            r.issues.append(Issue(
                Severity.WARNING, "POTENTIAL_DUPLICATES",
                f"{dups} node(s) share identical (label, lineNumber, filename) tuples.",
            ))

    def _check_orphan_nodes(self, g: nx.DiGraph, r: ValidationReport) -> None:
        orphans = [n for n in g.nodes if g.degree(n) == 0]
        if orphans:
            r.issues.append(Issue(
                Severity.WARNING, "ORPHAN_NODES",
                f"{len(orphans)} node(s) have no edges. This is normal for isolated declarations.",
            ))

    def _check_self_loops(self, g: nx.DiGraph, r: ValidationReport) -> None:
        loops = list(nx.selfloop_edges(g))
        if loops:
            r.issues.append(Issue(
                Severity.WARNING, "SELF_LOOPS",
                f"{len(loops)} self-loop edge(s) detected. These are unusual in a CPG.",
            ))
