# ============================================================
# PDF Report Generator (Phase 7 — ReportLab Platypus)
# ============================================================

from __future__ import annotations

import io
from datetime import datetime, timezone
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


class NumberedCanvas(canvas.Canvas):
    """Canvas that computes total page count dynamically for 'Page X of Y' footers."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            super().showPage()
        super().save()

    def draw_page_number(self, page_count: int):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))

        # Header rule & title
        self.setStrokeColor(colors.HexColor("#e2e8f0"))
        self.setLineWidth(0.5)
        self.line(40, letter[1] - 35, letter[0] - 40, letter[1] - 35)
        self.drawString(40, letter[1] - 30, "VulnScan Platform")

        # Footer
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.line(40, 40, letter[0] - 40, 40)
        self.drawString(40, 28, "CONFIDENTIAL — FOR AUTHORIZED SECURITY PERSONNEL ONLY")
        self.drawRightString(letter[0] - 40, 28, page_text)
        self.restoreState()


class PDFReportGenerator:
    """Generates professional, printable PDF security reports using ReportLab Platypus."""

    def generate(self, data: dict[str, Any], report_type: str = "security") -> bytes:
        """Produce PDF document bytes."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            leftMargin=40,
            rightMargin=40,
            topMargin=50,
            bottomMargin=50,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=26,
            textColor=colors.HexColor("#0f172a"),
        )
        subtitle_style = ParagraphStyle(
            "DocSubTitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=11,
            leading=15,
            textColor=colors.HexColor("#475569"),
        )
        h2_style = ParagraphStyle(
            "H2Style",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=17,
            textColor=colors.HexColor("#1e293b"),
            spaceBefore=10,
            spaceAfter=6,
        )
        body_style = ParagraphStyle(
            "ReportBody",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#334155"),
        )
        code_style = ParagraphStyle(
            "ReportCode",
            parent=styles["Normal"],
            fontName="Courier",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#0f172a"),
        )

        elements = []

        project = data.get("project", {})
        scan = data.get("scan", {})
        snapshot = data.get("snapshot", {})
        metrics = data.get("metrics", {})
        findings = data.get("findings", [])

        report_titles = {
            "developer": "Developer Remediation Report",
            "security": "Security Assessment Report",
            "executive": "Executive Security Posture Report",
        }
        title_text = report_titles.get(report_type, "Security Assessment Report")

        # Title and Header
        elements.append(Paragraph(title_text, title_style))
        elements.append(Paragraph(f"Project: <b>{project.get('name', 'N/A')}</b> &bull; Public ID: <code>{project.get('public_id', 'N/A')}</code>", subtitle_style))
        elements.append(Paragraph(f"Scan ID: <code>{scan.get('public_id', 'N/A')}</code> &bull; Snapshot: <code>{snapshot.get('commit_sha', 'HEAD')[:10]}</code> ({snapshot.get('branch', 'main')})", subtitle_style))
        elements.append(Spacer(1, 10))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cbd5e1"), spaceAfter=14))

        # KPI / Summary Table
        health_score = metrics.get("health_score", 100.0)
        health_rating = metrics.get("health_rating", "A")
        sev_counts = metrics.get("severity_counts", {})
        crit = sev_counts.get("critical", 0)
        high = sev_counts.get("high", 0)
        med = sev_counts.get("medium", 0)
        low = sev_counts.get("low", 0)

        summary_data = [
            ["Security Health Score", "Rating", "Total Findings", "Critical", "High", "Med & Low"],
            [
                f"{health_score}/100",
                f"Grade {health_rating}",
                str(len(findings)),
                str(crit),
                str(high),
                str(med + low),
            ],
        ]
        t_summary = Table(summary_data, colWidths=[90, 80, 80, 80, 80, 100])
        t_summary.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#475569")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("TEXTCOLOR", (3, 1), (3, 1), colors.HexColor("#ef4444")),  # Critical red
            ("TEXTCOLOR", (4, 1), (4, 1), colors.HexColor("#f97316")),  # High orange
            ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 1), (-1, 1), 11),
        ]))
        elements.append(t_summary)
        elements.append(Spacer(1, 14))

        # Executive Posture Section
        if report_type in ("executive", "security"):
            elements.append(Paragraph("Security Posture Overview", h2_style))
            posture_summary = (
                f"Analysis completed with a Security Health Score of <b>{health_score}/100 (Grade {health_rating})</b>. "
                f"There are currently <b>{len(findings)}</b> persistent findings identified across this snapshot. "
            )
            if crit > 0:
                crit_phrase = "Critical vulnerability requires" if crit == 1 else "Critical vulnerabilities require"
                posture_summary += f"<font color='#ef4444'><b>Immediate action required:</b> {crit} {crit_phrase} rapid remediation.</font>"
            else:
                posture_summary += "No Critical severity vulnerabilities were observed in this evaluation scope."

            elements.append(Paragraph(posture_summary, body_style))
            elements.append(Spacer(1, 10))

        # Findings Section
        if report_type == "executive":
            elements.append(Paragraph("Executive Findings Inventory", h2_style))
            rows = [["ID", "Title", "Severity", "CWE", "Status", "Risk Score"]]
            for f in findings:
                rows.append([
                    f.get("public_id", ""),
                    f.get("title", "")[:35],
                    f.get("severity", "").upper(),
                    f.get("cwe_id", "N/A"),
                    f.get("status", "OPEN"),
                    str(f.get("risk_score", 0.0)),
                ])
            if len(rows) == 1:
                rows.append(["None", "No persistent findings identified", "", "", "", ""])

            t_exec = Table(rows, colWidths=[70, 180, 70, 60, 70, 60])
            t_exec.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
            ]))
            elements.append(t_exec)
        else:
            # Detailed Developer or Security report
            elements.append(Paragraph(f"Detailed Findings ({len(findings)})", h2_style))
            if not findings:
                elements.append(Paragraph("No findings detected in this evaluation scope.", body_style))

            for f in findings:
                f_items = []
                sev = f.get("severity", "low").upper()
                sev_color = "#ef4444" if sev == "CRITICAL" else ("#f97316" if sev == "HIGH" else "#eab308")

                f_header = (
                    f"<font color='{sev_color}'><b>[{sev}]</b></font> "
                    f"<b>{f.get('title', 'Finding')}</b> "
                    f"<font color='#64748b'>(ID: {f.get('public_id')}, Finding Type: Vulnerability, CWE: {f.get('cwe_id', 'N/A')}, Status: {f.get('status', 'OPEN')})</font>"
                )
                f_items.append(Paragraph(f_header, body_style))

                # Occurrences
                occs = f.get("occurrences", [])
                if occs:
                    for occ in occs[:3]:  # list first 3 locations
                        loc_str = f"&bull; <code>{occ.get('file_path')}:{occ.get('start_line') or 1}</code> (Confidence: {occ.get('confidence', 0.0)})"
                        f_items.append(Paragraph(loc_str, body_style))

                # Developer remediations
                if report_type == "developer":
                    rems = f.get("remediations", [])
                    if rems:
                        rem = rems[0]
                        f_items.append(Spacer(1, 3))
                        f_items.append(Paragraph(f"<b>Remediation ({rem.get('validation_status', 'unvalidated')}):</b> {rem.get('explanation', '')[:200]}", body_style))

                f_items.append(Spacer(1, 6))
                elements.append(KeepTogether(f_items))

        # Build document
        doc.build(elements, canvasmaker=NumberedCanvas)
        return buffer.getvalue()
