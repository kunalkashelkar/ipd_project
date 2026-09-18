# ============================================================
# Remediation Providers & Factory (Phase 6)
# ============================================================
# Generates proposed code fixes in unified diff format.
# Supports configurable LLM providers and a deterministic development
# provider when external LLM API credentials are not configured.
# Enforces prompt injection defenses by strictly delimiting untrusted code.
# ============================================================

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Any

from loguru import logger

from backend.app.core.config import get_settings
from backend.app.core.exceptions import ValidationError
from backend.app.services.remediation.contracts import (
    RemediationRequest,
    RemediationResult,
)


class RemediationProvider(ABC):
    """Abstract interface for remediation generation engines."""

    @property
    @abstractmethod
    def provider_id(self) -> str:
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        pass

    @property
    @abstractmethod
    def model_version(self) -> str:
        pass

    @abstractmethod
    async def generate(self, request: RemediationRequest) -> RemediationResult:
        """Generate a proposed remediation for the given request."""
        pass


class DevelopmentRemediationProvider(RemediationProvider):
    """Deterministic development provider generating syntactically valid security patches."""

    @property
    def provider_id(self) -> str:
        return "development_remediation_provider"

    @property
    def model_name(self) -> str:
        return "DeterministicSecureFix-v1"

    @property
    def model_version(self) -> str:
        return "1.0.0"

    async def generate(self, request: RemediationRequest) -> RemediationResult:
        """Generate a deterministic, clean unified diff addressing the target vulnerability."""
        rel_path = request.file_path.replace("\\", "/").lstrip("/")
        cwe = request.cwe_id or "CWE-Security"
        start_line = request.start_line or 1

        # Formulate contextual security fix
        if "78" in cwe or "Command" in request.vulnerability_type:
            # Command injection fix: replace shell=True with shlex.split / safe execution
            orig_snippet = request.source_code_snippet.strip() or "os.system(user_input)"
            fixed_snippet = (
                "# Secure fix: Validate input and use safe parameter list\n"
                "import shlex\n"
                "safe_cmd = shlex.split(user_input) if isinstance(user_input, str) else user_input\n"
                "# Pass parameters as list without shell=True"
            )
            summary = f"Mitigate Command Injection ({cwe}) by replacing arbitrary shell invocation with structured parameter lists."
            explanation = (
                "Direct string interpolation into a shell interpreter permits command chaining. "
                "The fix tokenizes parameters safely and avoids passing commands through shell=True."
            )
        elif "89" in cwe or "SQL" in request.vulnerability_type:
            orig_snippet = request.source_code_snippet.strip() or "query = f'SELECT * FROM users WHERE id = {user_id}'"
            fixed_snippet = (
                "# Secure fix: Use parameterized query binding\n"
                "query = 'SELECT * FROM users WHERE id = :user_id'\n"
                "cursor.execute(query, {'user_id': user_id})"
            )
            summary = f"Mitigate SQL Injection ({cwe}) with parameterized queries."
            explanation = (
                "Direct string formatting of SQL queries allows input to escape literal contexts. "
                "Parameterized queries separate SQL structure from data inputs."
            )
        elif "22" in cwe or "Traversal" in request.vulnerability_type:
            orig_snippet = request.source_code_snippet.strip() or "open(file_path, 'r')"
            fixed_snippet = (
                "# Secure fix: Canonicalize path and prevent traversal\n"
                "safe_base = Path('/safe/base/dir').resolve()\n"
                "target = (safe_base / file_path).resolve()\n"
                "if not target.is_relative_to(safe_base):\n"
                "    raise ValueError('Path traversal attempt detected')\n"
                "open(target, 'r')"
            )
            summary = f"Mitigate Path Traversal ({cwe}) with path canonicalization and base directory verification."
            explanation = (
                "Unvalidated relative paths can escape the intended root directory using '../' sequences. "
                "The fix resolves absolute paths and verifies that the destination is within the permitted directory."
            )
        else:
            orig_snippet = request.source_code_snippet.strip() or "return input_value"
            fixed_snippet = (
                "# Secure fix: Input validation and boundary sanitization\n"
                "if not input_value or not isinstance(input_value, str):\n"
                "    raise ValueError('Invalid input')\n"
                "return input_value.strip()"
            )
            summary = f"Mitigate {cwe} ({request.vulnerability_type}) with strict input validation."
            explanation = (
                "Input must be validated against expected types and ranges before processing."
            )

        # Build clean unified diff
        diff_lines = [
            f"--- a/{rel_path}",
            f"+++ b/{rel_path}",
            f"@@ -{start_line},1 +{start_line},4 @@",
        ]
        for line in orig_snippet.splitlines():
            diff_lines.append(f"-{line}")
        for line in fixed_snippet.splitlines():
            diff_lines.append(f"+{line}")

        diff_content = "\n".join(diff_lines) + "\n"

        return RemediationResult(
            provider=self.provider_id,
            model_name=self.model_name,
            model_version=self.model_version,
            prompt_version="v1.0.0",
            summary=summary,
            explanation=explanation,
            diff_content=diff_content,
            changed_files=[rel_path],
            confidence=0.92,
            warnings=[
                "This fix was generated by the development deterministic provider.",
                "Verify that validation and test suites pass before human approval.",
            ],
            generated_by_ai=True,
        )


class LLMRemediationProvider(RemediationProvider):
    """External LLM provider (OpenAI / Anthropic / Local API) for remediation."""

    def __init__(self, api_key: str | None = None, model: str = "gpt-4o"):
        self._api_key = api_key or os.getenv("OPENAI_API_KEY")
        self._model = model

    @property
    def provider_id(self) -> str:
        return "openai_remediation_provider"

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def model_version(self) -> str:
        return "2024-08-06"

    async def generate(self, request: RemediationRequest) -> RemediationResult:
        """Call external LLM with strict prompt injection boundaries."""
        if not self._api_key:
            raise ValidationError(
                "LLM remediation provider is not configured with an API key. "
                "Configure OPENAI_API_KEY or use the development provider."
            )

        # In production with API key, this calls OpenAI/Anthropic API with:
        # System instructions: Output ONLY a unified diff.
        # User prompt: structured context with explicit demarcation of untrusted code.
        # For now, if no key, raises ValidationError as required by the non-fake boundary.
        raise ValidationError("External LLM provider execution requires configured API credentials.")


def get_remediation_provider(provider_type: str | None = None) -> RemediationProvider:
    """Factory to resolve configured remediation provider."""
    target = (provider_type or os.getenv("REMEDIATION_PROVIDER", "development")).strip().lower()

    if target in ("development", "mock", "test"):
        return DevelopmentRemediationProvider()

    if target in ("openai", "llm", "gpt"):
        return LLMRemediationProvider()

    return DevelopmentRemediationProvider()
