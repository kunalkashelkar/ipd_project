# ============================================================
# PDF Report Generator
# ============================================================

from __future__ import annotations

from typing import Any

from backend.app.reports.generator import ReportGenerator


class PDFReportGenerator(ReportGenerator):
    """Generates human-readable PDF reports.

    (Mock implementation for MVP. Real implementation would use reportlab or weasyprint)
    """

    @property
    def extension(self) -> str:
        return ".pdf"

    def generate(self, scan_id: str, results: list[dict], metadata: dict[str, Any]) -> bytes:
        """Mock PDF generation."""
        # For a real implementation, you would construct a PDF canvas here.
        # Returning dummy bytes for now.
        dummy_content = (
            f"PDF Report for Scan: {scan_id}\n"
            f"Total Findings: {len(results)}\n"
            "This is a placeholder for the PDF binary data.\n"
        )
        return dummy_content.encode("utf-8")
