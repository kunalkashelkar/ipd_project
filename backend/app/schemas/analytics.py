# ============================================================
# Analytics Schemas
# ============================================================

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class SeverityBreakdown(BaseModel):
    """Vulnerability severity breakdown."""

    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    info: int = 0


class DashboardResponse(BaseModel):
    """Dashboard analytics data."""

    total_projects: int = 0
    total_scans: int = 0
    completed_scans: int = 0
    failed_scans: int = 0
    total_vulnerabilities: int = 0
    severity_breakdown: SeverityBreakdown = SeverityBreakdown()
    recent_scans: list[dict[str, Any]] = []
    scan_success_rate: float = 0.0
    vulnerabilities_by_cwe: list[dict[str, Any]] = []
