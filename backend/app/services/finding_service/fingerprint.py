# ============================================================
# Finding Fingerprinting Algorithm (Phase 5)
# ============================================================
# Generates deterministic, immutable SHA-256 fingerprints
# for vulnerability findings across repeated scans.
#
# Algorithm (v1.0):
#   Key Components:
#     1. cwe_id: Normalized uppercase CWE identifier (e.g. "CWE-89")
#     2. normalized_path: Lowercase forward-slash relative path (e.g. "app/routes.py")
#     3. function_name: Extracted function name or '<global>'
#     4. stable_context: Normalized sink identity or code region
#
#   Formula:
#     RAW = f"{cwe}:{path}:{function}:{context}"
#     FINGERPRINT = sha256(RAW.encode("utf-8")).hexdigest()
# ============================================================

from __future__ import annotations

import hashlib
from typing import Any

CURRENT_FINGERPRINT_VERSION = "v1.0"


def compute_finding_fingerprint(
    *,
    cwe_id: str | None,
    file_path: str,
    function_name: str | None = None,
    line_number: int | None = None,
    evidence: dict[str, Any] | None = None,
    version: str = CURRENT_FINGERPRINT_VERSION,
) -> tuple[str, str]:
    """Compute a deterministic, stable fingerprint for a vulnerability finding.
    
    Returns:
        (fingerprint_hash, fingerprint_version)
    """
    normalized_cwe = (cwe_id or "UNKNOWN").strip().upper()
    normalized_path = file_path.replace("\\", "/").strip().lower()
    normalized_fn = (function_name or "<global>").strip().lower()

    if version == "v1.0":
        # Check if evidence contains a specific sink or pattern hint
        sink_hint = ""
        if evidence:
            sink_hint = str(
                evidence.get("matched_pattern")
                or evidence.get("sink_id")
                or evidence.get("vulnerability_type")
                or ""
            ).strip().lower()

        # Line number is bucketed into function context if function is present;
        # otherwise normalized line number is used
        location_token = sink_hint if sink_hint else str(line_number or 0)

        raw_key = f"{normalized_cwe}:{normalized_path}:{normalized_fn}:{location_token}"
        fingerprint = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
        return fingerprint, "v1.0"

    raise ValueError(f"Unsupported fingerprint version: {version}")
