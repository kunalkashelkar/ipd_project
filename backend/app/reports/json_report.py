# ============================================================
# JSON Report Generator
# ============================================================

from __future__ import annotations

import json
from typing import Any

from backend.app.reports.generator import ReportGenerator


class JSONReportGenerator(ReportGenerator):
    """Generates machine-readable JSON reports."""

    @property
    def extension(self) -> str:
        return ".json"

    def generate(self, scan_id: str, results: list[dict], metadata: dict[str, Any]) -> bytes:
        """Format results as pretty JSON."""
        report = {
            "metadata": metadata,
            "scan_id": scan_id,
            "total_findings": len(results),
            "findings": results,
        }
        return json.dumps(report, indent=2).encode("utf-8")
