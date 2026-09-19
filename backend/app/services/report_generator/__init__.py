# ============================================================
# Report Generator Package (Phase 7)
# ============================================================

from __future__ import annotations

from typing import Any

from backend.app.services.report_generator.csv_generator import CSVReportGenerator
from backend.app.services.report_generator.data_collector import ReportDataCollector
from backend.app.services.report_generator.html_generator import HTMLReportGenerator
from backend.app.services.report_generator.json_generator import JSONReportGenerator
from backend.app.services.report_generator.pdf_generator import PDFReportGenerator


class ReportGenerator:
    """Unified report generator supporting Developer, Security, Executive in PDF, HTML, JSON, CSV."""

    def __init__(self):
        self.json_gen = JSONReportGenerator()
        self.csv_gen = CSVReportGenerator()
        self.html_gen = HTMLReportGenerator()
        self.pdf_gen = PDFReportGenerator()

    def generate(self, data: dict[str, Any], report_type: str, format: str) -> tuple[bytes, str]:
        """Generate report content bytes and content type."""
        fmt = format.lower().strip()
        rtype = report_type.lower().strip()
        if rtype not in ("developer", "security", "executive"):
            rtype = "security"

        if fmt == "pdf":
            return self.pdf_gen.generate(data, report_type=rtype), "application/pdf"
        elif fmt == "html":
            return self.html_gen.generate(data, report_type=rtype), "text/html; charset=utf-8"
        elif fmt == "csv":
            return self.csv_gen.generate(data, report_type=rtype), "text/csv; charset=utf-8"
        elif fmt == "json":
            return self.json_gen.generate(data, report_type=rtype), "application/json"
        else:
            raise ValueError(f"Unsupported report format: '{format}'. Supported formats: pdf, html, json, csv")


__all__ = [
    "CSVReportGenerator",
    "HTMLReportGenerator",
    "JSONReportGenerator",
    "PDFReportGenerator",
    "ReportDataCollector",
    "ReportGenerator",
]
