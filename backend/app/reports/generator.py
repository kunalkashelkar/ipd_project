# ============================================================
# Report Generator Interface
# ============================================================

from __future__ import annotations

import abc
from typing import Any


class ReportGenerator(abc.ABC):
    """Abstract base class for all report generators."""

    @abc.abstractmethod
    def generate(self, scan_id: str, results: list[dict], metadata: dict[str, Any]) -> bytes:
        """Generate a report from scan results and return as bytes."""
        pass

    @property
    @abc.abstractmethod
    def extension(self) -> str:
        """Return the file extension for this report type (e.g., '.json')."""
        pass
