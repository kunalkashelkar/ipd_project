# ============================================================
# CSV Report Generator (Phase 7)
# ============================================================

from __future__ import annotations

import csv
import io
from typing import Any


class CSVReportGenerator:
    """Generates RFC 4180 compliant CSV exports with formula injection protection."""

    @staticmethod
    def _sanitize(val: Any) -> str:
        """Sanitize text to prevent CSV injection (=, +, -, @)."""
        if val is None:
            return ""
        s = str(val).strip()
        if s and s[0] in ("=", "+", "-", "@", "\t", "\r"):
            return f"'{s}"
        return s

    def generate(self, data: dict[str, Any], report_type: str = "security") -> bytes:
        """Produce CSV bytes for findings and occurrences."""
        output = io.StringIO()
        writer = csv.writer(output, dialect="excel")

        if report_type == "executive":
            # High-level executive rows
            writer.writerow([
                "Finding ID",
                "Title",
                "Severity",
                "CWE ID",
                "Status",
                "Risk Score",
                "CVSS Score",
                "First Seen",
            ])
            for f in data.get("findings", []):
                writer.writerow([
                    self._sanitize(f.get("public_id")),
                    self._sanitize(f.get("title")),
                    self._sanitize(f.get("severity", "").upper()),
                    self._sanitize(f.get("cwe_id")),
                    self._sanitize(f.get("status")),
                    self._sanitize(f.get("risk_score")),
                    self._sanitize(f.get("cvss_score") or "N/A"),
                    self._sanitize(f.get("first_seen_at")),
                ])
        else:
            # Detailed Developer / Security rows
            writer.writerow([
                "Finding ID",
                "Title",
                "Finding Type",
                "Severity",
                "CWE ID",
                "Status",
                "Risk Score",
                "Confidence",
                "File Path",
                "Start Line",
                "End Line",
                "Remediation Available",
                "Validation Status",
                "First Seen",
                "Last Seen",
            ])
            for f in data.get("findings", []):
                occurrences = f.get("occurrences", [])
                remediations = f.get("remediations", [])
                has_rem = "YES" if remediations else "NO"
                val_status = remediations[0].get("validation_status", "N/A") if remediations else "N/A"

                if occurrences:
                    for occ in occurrences:
                        writer.writerow([
                            self._sanitize(f.get("public_id")),
                            self._sanitize(f.get("title")),
                            self._sanitize(f.get("vulnerability_type")),
                            self._sanitize(f.get("severity", "").upper()),
                            self._sanitize(f.get("cwe_id")),
                            self._sanitize(f.get("status")),
                            self._sanitize(f.get("risk_score")),
                            self._sanitize(occ.get("confidence") or f.get("confidence")),
                            self._sanitize(occ.get("file_path")),
                            self._sanitize(occ.get("start_line") or "N/A"),
                            self._sanitize(occ.get("end_line") or "N/A"),
                            self._sanitize(has_rem),
                            self._sanitize(val_status),
                            self._sanitize(f.get("first_seen_at")),
                            self._sanitize(f.get("last_seen_at")),
                        ])
                else:
                    writer.writerow([
                        self._sanitize(f.get("public_id")),
                        self._sanitize(f.get("title")),
                        self._sanitize(f.get("vulnerability_type")),
                        self._sanitize(f.get("severity", "").upper()),
                        self._sanitize(f.get("cwe_id")),
                        self._sanitize(f.get("status")),
                        self._sanitize(f.get("risk_score")),
                        self._sanitize(f.get("confidence")),
                        "",
                        "",
                        "",
                        self._sanitize(has_rem),
                        self._sanitize(val_status),
                        self._sanitize(f.get("first_seen_at")),
                        self._sanitize(f.get("last_seen_at")),
                    ])

        return output.getvalue().encode("utf-8-sig")
