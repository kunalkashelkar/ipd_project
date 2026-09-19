# ============================================================
# Analytics Schemas (Phase 7)
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


class HealthScoreDetail(BaseModel):
    """Authoritative Security Health Score details."""

    score: float | None = None
    rating: str | None = None
    version: str = "v1.0.0"
    penalties_applied: float = 0.0
    recovery_bonus: float = 0.0
    status: str = "SCORED"
    message: str | None = None


class DashboardResponse(BaseModel):
    """Dashboard analytics posture data."""

    total_projects: int = 0
    total_scans: int = 0
    completed_scans: int = 0
    failed_scans: int = 0
    total_vulnerabilities: int = 0
    severity_breakdown: SeverityBreakdown = SeverityBreakdown()
    recent_scans: list[dict[str, Any]] = []
    scan_success_rate: float = 0.0
    vulnerabilities_by_cwe: list[dict[str, Any]] = []
    health_score: float | None = None
    health_rating: str | None = None
    health_status: str = "SCORED"
    score_version: str = "v1.0.0"


class AnalyticsMetricsResponse(BaseModel):
    """Deep authoritative analytics response."""

    health_score: HealthScoreDetail
    active_findings: int = 0
    total_findings: int = 0
    new_findings: int = 0
    resolved_findings: int = 0
    critical_findings: int = 0
    severity_breakdown: SeverityBreakdown
    cwe_distribution: list[dict[str, Any]]
    finding_trends: list[dict[str, Any]]
    risk_trends: list[dict[str, Any]]
    mttr_hours: float | None = None
    remediation_rate: float = 0.0
    false_positive_rate: float = 0.0
    ai_metrics: dict[str, Any]
    repository_stats: list[dict[str, Any]]


class ScanComparisonResponse(BaseModel):
    """Authoritative scan-to-scan finding comparison."""

    baseline_scan_id: str
    current_scan_id: str
    existing_count: int = 0
    new_count: int = 0
    fixed_count: int = 0
    reopened_count: int = 0
    existing_findings: list[dict[str, Any]] = []
    new_findings: list[dict[str, Any]] = []
    fixed_findings: list[dict[str, Any]] = []
    reopened_findings: list[dict[str, Any]] = []
