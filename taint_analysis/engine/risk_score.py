# ============================================================
# Taint Engine — Risk Scorer
# ============================================================
# Assigns a composite 0–10 risk score to each AttackPath using
# a weighted scoring model based on CWE severity research.
# ============================================================

from __future__ import annotations

from taint_analysis.models.path import AttackPath

# Sink category → base risk points (max 4 points)
_SINK_BASE_SCORES: dict[str, float] = {
    "command_injection":  4.0,
    "buffer_overflow":    3.5,
    "format_string":      3.0,
    "sql_injection":      3.5,
    "path_traversal":     2.5,
    "heap_overflow":      3.0,
    "integer_overflow":   2.0,
}

# Source category → risk multiplier bonus (max 1 point)
_SOURCE_BONUS: dict[str, float] = {
    "network":   1.0,
    "functions": 0.8,   # stdin-based sources
    "env_vars":  0.5,
    "argv":      0.6,
    "file_io":   0.4,
    "ipc":       0.7,
}

# Severity thresholds
_SEVERITY_TABLE: list[tuple[float, str]] = [
    (9.0, "CRITICAL"),
    (7.0, "HIGH"),
    (4.0, "MEDIUM"),
    (1.0, "LOW"),
    (0.0, "SAFE"),
]


class RiskScorer:
    """Scores an attack path on a 0–10 scale and classifies severity.

    Scoring model:
    ┌─────────────────────────────────┬─────────────┐
    │ Factor                          │ Max Points  │
    ├─────────────────────────────────┼─────────────┤
    │ Sink category                   │ 4.0         │
    │ Short path (≤ 3 hops)           │ 2.0         │
    │ Source category bonus           │ 1.0         │
    │ Unsanitized (no sanitizer)      │ 2.0         │
    │ Multi-source convergence (+)    │ 1.0         │
    ├─────────────────────────────────┼─────────────┤
    │ Total (before clamp)            │ 10.0        │
    └─────────────────────────────────┴─────────────┘
    """

    def score(
        self,
        path: AttackPath,
        multi_source: bool = False,
    ) -> float:
        """Compute a 0–10 risk score for *path*.

        Args:
            path:         The attack path to score.
            multi_source: True if multiple source flows reach the same sink.

        Returns:
            Float score clamped to [0, 10].
        """
        total = 0.0

        # ── Sink category base score (0–4) ─────────────────
        total += _SINK_BASE_SCORES.get(path.sink_category, 1.0)

        # ── Path length factor (0–2) ───────────────────────
        # Shorter paths = more directly exploitable = higher risk
        if path.length <= 2:
            total += 2.0
        elif path.length <= 5:
            total += 1.5
        elif path.length <= 10:
            total += 1.0
        else:
            total += 0.5

        # ── Source category bonus (0–1) ────────────────────
        total += _SOURCE_BONUS.get(path.source_category, 0.3)

        # ── Sanitization penalty (0 or –3) ─────────────────
        # Fully sanitized paths still score (sanitizer may be bypassable)
        # but get a heavy penalty
        if not path.sanitized:
            total += 2.0   # bonus for LACK of sanitization
        else:
            total -= 2.0   # heavy penalty for being sanitized

        # ── Multi-source convergence bonus (0–1) ───────────
        if multi_source:
            total += 1.0

        return round(max(0.0, min(10.0, total)), 2)

    def classify(self, score: float) -> str:
        """Return the severity label for a given score."""
        for threshold, label in _SEVERITY_TABLE:
            if score >= threshold:
                return label
        return "SAFE"

    def score_and_classify(
        self,
        path: AttackPath,
        multi_source: bool = False,
    ) -> tuple[float, str]:
        """Convenience: score and classify in one call."""
        s = self.score(path, multi_source)
        return s, self.classify(s)

    def count_by_severity(self, paths: list[AttackPath]) -> dict[str, int]:
        """Return severity distribution dict over a list of paths."""
        counts: dict[str, int] = {
            "CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "SAFE": 0
        }
        for p in paths:
            counts[p.severity] = counts.get(p.severity, 0) + 1
        return counts
