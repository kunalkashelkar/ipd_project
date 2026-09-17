# ============================================================
# Mock AI Inference Provider
# ============================================================
# Temporary implementation of the permanent AIInferenceProvider boundary.
# Used exclusively for development and automated pipeline testing.
# Guarantees:
# - Deterministic & reproducible (hash-seeded)
# - Location-valid (only actual snapshot files and function line ranges)
# - Clearly records mock provenance
# ============================================================

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from backend.app.services.ai_inference.base import AIInferenceProvider
from backend.app.services.ai_inference.contracts import (
    AIErrorCode,
    AIInferenceError,
    CanonicalAIPrediction,
    CanonicalAIRequest,
)

# Standard deterministic vulnerability archetypes for realistic exercising of UI & correlation
MOCK_VULN_ARCHETYPES = [
    {
        "cwe_id": "CWE-89",
        "title": "Improper Neutralization of Special Elements used in an SQL Command ('SQL Injection')",
        "severity": "critical",
        "cvss_score": 9.2,
        "base_confidence": 0.94,
        "pattern_hints": ["query", "select", "sql", "execute", "db", "user", "input"],
        "category": "Injection",
    },
    {
        "cwe_id": "CWE-78",
        "title": "Improper Neutralization of Special Elements used in an OS Command ('OS Command Injection')",
        "severity": "critical",
        "cvss_score": 9.8,
        "base_confidence": 0.91,
        "pattern_hints": ["cmd", "exec", "system", "popen", "spawn", "shell", "run"],
        "category": "Injection",
    },
    {
        "cwe_id": "CWE-79",
        "title": "Improper Neutralization of Input During Web Page Generation ('Cross-site Scripting')",
        "severity": "high",
        "cvss_score": 7.4,
        "base_confidence": 0.88,
        "pattern_hints": ["render", "html", "response", "echo", "write", "template", "view"],
        "category": "Cross-Site Scripting",
    },
    {
        "cwe_id": "CWE-22",
        "title": "Improper Limitation of a Pathname to a Restricted Directory ('Path Traversal')",
        "severity": "high",
        "cvss_score": 7.5,
        "base_confidence": 0.86,
        "pattern_hints": ["path", "file", "open", "read", "load", "dir", "upload"],
        "category": "Path Traversal",
    },
    {
        "cwe_id": "CWE-352",
        "title": "Cross-Site Request Forgery (CSRF)",
        "severity": "medium",
        "cvss_score": 6.5,
        "base_confidence": 0.82,
        "pattern_hints": ["post", "action", "auth", "token", "form", "submit"],
        "category": "Session Management",
    },
]


class MockAIProvider(AIInferenceProvider):
    """Deterministic, contract-compliant mock AI inference provider."""

    @property
    def provider_id(self) -> str:
        return "mock"

    @property
    def model_name(self) -> str:
        return "MockAIProvider"

    @property
    def model_version(self) -> str:
        return "mock-1.0.0"

    async def predict(self, request: CanonicalAIRequest) -> list[CanonicalAIPrediction]:
        """Generate deterministic, location-valid predictions derived from real snapshot code."""
        if not request.source_files and not request.functions:
            return []

        # Validate language support if specified
        supported_langs = {"python", "javascript", "typescript", "c", "cpp", "java", "go"}
        if request.language and request.language.lower() not in supported_langs:
            raise AIInferenceError(
                code=AIErrorCode.UNSUPPORTED_LANGUAGE,
                message=f"Language '{request.language}' is not supported by {self.model_name}",
                details={"supported_languages": sorted(list(supported_langs))},
            )

        predictions: list[CanonicalAIPrediction] = []

        # Group functions by relative path
        funcs_by_path: dict[str, list[Any]] = {}
        for fn in request.functions:
            funcs_by_path.setdefault(fn.relative_path, []).append(fn)

        # Iterate deterministically over source files in request
        sorted_files = sorted(request.source_files, key=lambda f: f.relative_path)
        for sfile in sorted_files:
            rel_path = sfile.relative_path
            norm_path = rel_path.lower()

            # Skip common non-code / config assets
            if any(norm_path.endswith(ext) for ext in [".json", ".md", ".txt", ".yml", ".yaml", ".toml"]):
                continue

            # Deterministic hash derived from snapshot ID + file relative path
            path_seed = hashlib.sha256(f"{request.source_snapshot_id}:{rel_path}".encode("utf-8")).hexdigest()
            seed_int = int(path_seed[:8], 16)

            functions_in_file = funcs_by_path.get(rel_path, [])

            if functions_in_file:
                # Deterministically check functions in this file
                for fn in sorted(functions_in_file, key=lambda f: (f.start_line, f.name)):
                    fn_seed = hashlib.sha256(f"{path_seed}:{fn.name}:{fn.start_line}".encode("utf-8")).hexdigest()
                    fn_int = int(fn_seed[:8], 16)

                    # Match with an archetype if function name or signature matches pattern hints
                    matched_archetype = None
                    search_text = f"{fn.name} {fn.signature or ''} {rel_path}".lower()
                    for arch in MOCK_VULN_ARCHETYPES:
                        if any(hint in search_text for hint in arch["pattern_hints"]):
                            matched_archetype = arch
                            break

                    # If no keyword matched, use deterministic modulo to distribute realistic coverage (e.g. ~35% hit rate)
                    if not matched_archetype and (fn_int % 3 == 0):
                        arch_idx = (fn_int // 3) % len(MOCK_VULN_ARCHETYPES)
                        matched_archetype = MOCK_VULN_ARCHETYPES[arch_idx]

                    if matched_archetype:
                        # Pick a deterministic line within the actual function boundaries
                        line_span = max(1, fn.end_line - fn.start_line)
                        vuln_line = fn.start_line + (fn_int % line_span)

                        # Small deterministic jitter on confidence
                        jitter = ((fn_int % 100) - 50) / 1000.0  # -0.05 to +0.05
                        confidence = round(min(0.99, max(0.65, matched_archetype["base_confidence"] + jitter)), 2)

                        predictions.append(
                            CanonicalAIPrediction(
                                file_path=rel_path,
                                function_name=fn.name,
                                line_number=vuln_line,
                                end_line=vuln_line,
                                prediction="VULNERABLE",
                                confidence=confidence,
                                cwe_id=matched_archetype["cwe_id"],
                                severity=matched_archetype["severity"],
                                cvss_score=matched_archetype["cvss_score"],
                                evidence={
                                    "vulnerability_type": matched_archetype["title"],
                                    "detection_source": "mock_rule_engine",
                                    "matched_pattern": matched_archetype["category"],
                                    "function_signature": fn.signature or fn.name,
                                    "function_range": [fn.start_line, fn.end_line],
                                    "graph_context": {
                                        "cpg_reference": request.cpg_ref,
                                        "taint_reference": request.taint_evidence_ref,
                                    },
                                },
                                provider=self.provider_id,
                                model_name=self.model_name,
                                model_version=self.model_version,
                                input_schema_version=request.feature_schema_version,
                                output_schema_version="v1.0.0",
                                generated_by_ai=True,
                                inference_timestamp=datetime.now(timezone.utc),
                                provenance_metadata={
                                    "is_mock": True,
                                    "scan_id": str(request.scan_id),
                                    "snapshot_id": str(request.source_snapshot_id),
                                    "note": "Deterministic development inference for Phase 5 platform testing",
                                },
                            )
                        )
            else:
                # File has no parsed functions, but check if file itself is a code file with valid lines
                if sfile.line_count > 0 and (seed_int % 4 == 0):
                    arch_idx = seed_int % len(MOCK_VULN_ARCHETYPES)
                    arch = MOCK_VULN_ARCHETYPES[arch_idx]
                    vuln_line = max(1, min(sfile.line_count, (seed_int % sfile.line_count) + 1))
                    confidence = arch["base_confidence"]

                    predictions.append(
                        CanonicalAIPrediction(
                            file_path=rel_path,
                            function_name=None,
                            line_number=vuln_line,
                            end_line=vuln_line,
                            prediction="VULNERABLE",
                            confidence=confidence,
                            cwe_id=arch["cwe_id"],
                            severity=arch["severity"],
                            cvss_score=arch["cvss_score"],
                            evidence={
                                "vulnerability_type": arch["title"],
                                "detection_source": "mock_file_heuristics",
                                "matched_pattern": arch["category"],
                            },
                            provider=self.provider_id,
                            model_name=self.model_name,
                            model_version=self.model_version,
                            input_schema_version=request.feature_schema_version,
                            output_schema_version="v1.0.0",
                            generated_by_ai=True,
                            inference_timestamp=datetime.now(timezone.utc),
                            provenance_metadata={
                                "is_mock": True,
                                "scan_id": str(request.scan_id),
                                "snapshot_id": str(request.source_snapshot_id),
                            },
                        )
                    )

        # Cap predictions deterministically to avoid overwhelming the system
        return predictions[:25]
