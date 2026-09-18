# ============================================================
# Remediation & Patch Contracts (Phase 6)
# ============================================================
# Canonical data structures for remediation requests, results,
# unified diff patches, and validation checks.
# ============================================================

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RemediationRequest:
    """Structured context provided to the RemediationProvider."""

    finding_id: uuid.UUID
    cwe_id: str | None
    vulnerability_type: str
    file_path: str
    function_name: str | None
    start_line: int | None
    end_line: int | None
    source_code_snippet: str
    surrounding_context: str | None = None
    taint_flow_summary: str | None = None
    explanation_summary: str | None = None
    root_cause: str | None = None
    constraints: list[str] = field(default_factory=list)


@dataclass
class RemediationResult:
    """Canonical remediation proposal output by any RemediationProvider."""

    provider: str
    model_name: str
    model_version: str
    prompt_version: str
    summary: str
    explanation: str
    diff_content: str  # Unified diff format
    changed_files: list[str]
    confidence: float | None = None
    warnings: list[str] = field(default_factory=list)
    generated_by_ai: bool = True
