# ============================================================
# JSON Report Generator (Phase 7)
# ============================================================

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any


class JSONReportGenerator:
    """Generates structured, versioned JSON security reports."""

    SCHEMA_VERSION = "1.0.0"

    def generate(self, data: dict[str, Any], report_type: str = "security") -> bytes:
        """Produce versioned JSON bytes."""
        payload = {
            "schema_version": self.SCHEMA_VERSION,
            "report_type": report_type,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "generator": "VulnScan-Platform",
            "project": data.get("project", {}),
            "organization": data.get("organization", {}),
            "scan": data.get("scan", {}),
            "snapshot": data.get("snapshot", {}),
            "metrics": data.get("metrics", {}),
        }

        # Executive report omits granular occurrence and code details
        if report_type == "executive":
            payload["findings_summary"] = [
                {
                    "public_id": f.get("public_id"),
                    "title": f.get("title"),
                    "severity": f.get("severity"),
                    "cwe_id": f.get("cwe_id"),
                    "status": f.get("status"),
                    "risk_score": f.get("risk_score"),
                }
                for f in data.get("findings", [])
            ]
        else:
            payload["findings"] = data.get("findings", [])

        return json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
