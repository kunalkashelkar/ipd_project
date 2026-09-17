# ============================================================
# Versioned Risk Calculation Engine (Phase 5)
# ============================================================
# Deterministic calculation of finding risk scores.
# Formula (v1.0):
#   Base Severity Weight:
#     critical: 10.0
#     high: 8.0
#     medium: 5.0
#     low: 2.5
#     info/other: 1.0
#
#   CVSS Contribution:
#     If cvss_score is provided: base = 0.5 * severity_weight + 0.5 * cvss_score
#     Else: base = severity_weight
#
#   Confidence Multiplier:
#     conf_multiplier = 0.5 + 0.5 * confidence  (maps 0.0-1.0 to 0.5-1.0)
#
#   Reachability / Taint Multiplier:
#     reach_multiplier = 1.15 if has_taint_flow else 1.0
#
#   Final Risk Score:
#     risk_score = round(min(10.0, max(0.0, base * conf_multiplier * reach_multiplier)), 1)
# ============================================================

from __future__ import annotations

from typing import Any

CURRENT_RISK_VERSION = "v1.0"

SEVERITY_WEIGHTS: dict[str, float] = {
    "critical": 10.0,
    "high": 8.0,
    "medium": 5.0,
    "low": 2.5,
    "info": 1.0,
}


def calculate_risk_score(
    *,
    severity: str,
    confidence: float,
    cvss_score: float | None = None,
    has_taint_flow: bool = False,
    extra_context: dict[str, Any] | None = None,
    version: str = CURRENT_RISK_VERSION,
) -> tuple[float, str]:
    """Calculate deterministic risk score on a 0.0 - 10.0 scale.
    
    Returns:
        (risk_score, risk_version)
    """
    if version == "v1.0":
        sev_key = severity.lower().strip()
        sev_weight = SEVERITY_WEIGHTS.get(sev_key, 5.0)

        if cvss_score is not None and 0.0 <= cvss_score <= 10.0:
            base = 0.5 * sev_weight + 0.5 * cvss_score
        else:
            base = sev_weight

        # Confidence scaling: high confidence maintains full score, lower confidence dampens it
        conf_scaled = max(0.0, min(1.0, confidence))
        conf_multiplier = 0.5 + (0.5 * conf_scaled)

        # Reachability factor
        reach_multiplier = 1.15 if has_taint_flow else 1.0

        raw_score = base * conf_multiplier * reach_multiplier
        risk_score = round(min(10.0, max(0.0, raw_score)), 1)
        return risk_score, "v1.0"

    raise ValueError(f"Unsupported risk calculation version: {version}")
