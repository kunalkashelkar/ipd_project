# ============================================================
# Lightweight Application Metrics Collector (Phase 8)
# ============================================================
# In-memory accumulator for operational health, API latency,
# scan stage durations, and error rates without external agents.
# Guarantees zero leakage of tenant data or secrets.
# ============================================================

from __future__ import annotations

import threading
import time
from collections import defaultdict
from typing import Any


class MetricsCollector:
    """Thread-safe, lightweight operational metrics collector."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[str, int] = defaultdict(int)
        self._histograms: dict[str, list[float]] = defaultdict(list)
        self._start_time = time.time()

    def increment(self, metric: str, value: int = 1) -> None:
        """Increment a monotonic counter."""
        with self._lock:
            self._counters[metric] += value

    def observe(self, metric: str, value: float) -> None:
        """Record a latency or duration measurement."""
        with self._lock:
            hist = self._histograms[metric]
            hist.append(value)
            # Bound memory: retain last 1,000 observations per metric
            if len(hist) > 1000:
                self._histograms[metric] = hist[-1000:]

    def get_snapshot(self) -> dict[str, Any]:
        """Produce an aggregated operational snapshot."""
        with self._lock:
            uptime = max(0.0, time.time() - self._start_time)
            counters = dict(self._counters)

            summaries = {}
            for k, vals in self._histograms.items():
                if vals:
                    summaries[k] = {
                        "count": len(vals),
                        "avg": round(sum(vals) / len(vals), 3),
                        "min": round(min(vals), 3),
                        "max": round(max(vals), 3),
                    }
                else:
                    summaries[k] = {"count": 0, "avg": 0.0, "min": 0.0, "max": 0.0}

            return {
                "uptime_seconds": round(uptime, 1),
                "counters": counters,
                "durations": summaries,
            }

    def reset(self) -> None:
        """Reset all metrics (primarily for test fixture isolation)."""
        with self._lock:
            self._counters.clear()
            self._histograms.clear()
            self._start_time = time.time()


# Global singleton instance
metrics = MetricsCollector()
