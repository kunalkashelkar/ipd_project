# ============================================================
# CSV Report Generator
# ============================================================

from __future__ import annotations

import csv
import io
from typing import Any

from backend.app.reports.generator import ReportGenerator


class CSVReportGenerator(ReportGenerator):
    """Generates tabular CSV reports."""

    @property
    def extension(self) -> str:
        return ".csv"

    def generate(self, scan_id: str, results: list[dict], metadata: dict[str, Any]) -> bytes:
        """Format results as CSV data."""
        if not results:
            return b"No vulnerabilities found."

        output = io.StringIO()
        fieldnames = [
            "file_path",
            "function_name",
            "line_number",
            "severity",
            "confidence",
            "cwe_id",
            "explanation",
            "recommended_patch",
            "model_version",
        ]

        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for r in results:
            writer.writerow(r)

        return output.getvalue().encode("utf-8")
