# ============================================================
# Finding Service Subsystem
# ============================================================

from backend.app.services.finding_service.correlation import FindingCorrelationService
from backend.app.services.finding_service.fingerprint import (
    CURRENT_FINGERPRINT_VERSION,
    compute_finding_fingerprint,
)
from backend.app.services.finding_service.lifecycle import (
    ALLOWED_TRANSITIONS,
    FindingLifecycleService,
)
from backend.app.services.finding_service.risk import (
    CURRENT_RISK_VERSION,
    calculate_risk_score,
)

__all__ = [
    "FindingCorrelationService",
    "FindingLifecycleService",
    "compute_finding_fingerprint",
    "calculate_risk_score",
    "ALLOWED_TRANSITIONS",
    "CURRENT_FINGERPRINT_VERSION",
    "CURRENT_RISK_VERSION",
]
