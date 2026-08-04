# ============================================================
# Joern Integration — CLI Runner
# ============================================================
# Executes joern-parse and joern-export as subprocesses.
# Raises typed exceptions on failure. All output is captured
# and logged at DEBUG level so logs stay clean by default.
# ============================================================

from __future__ import annotations

import subprocess
from pathlib import Path

from loguru import logger

from parser.joern.config import JoernConfig, get_joern_config


class JoernError(Exception):
    """Base class for Joern execution errors."""


class JoernParseError(JoernError):
    """Raised when joern-parse exits with a non-zero return code."""


class JoernExportError(JoernError):
    """Raised when joern-export exits with a non-zero return code."""


class JoernNotFoundError(JoernError):
    """Raised when the Joern binaries cannot be located."""


class JoernRunner:
    """Thin wrapper around the Joern CLI tools.

    Attributes:
        config: JoernConfig instance (injected or loaded from env).
    """

    def __init__(self, config: JoernConfig | None = None) -> None:
        self.config = config or get_joern_config()
        if not self.config.is_joern_available():
            raise JoernNotFoundError(
                f"Joern CLI binaries not found at '{self.config.joern_cli_dir}'. "
                "Set JOERN_HOME in your .env or install Joern."
            )

    # ── Public API ─────────────────────────────────────────

    def parse(self, source_dir: Path, output_cpg: Path) -> None:
        """Run joern-parse on *source_dir*, writing the CPG binary to *output_cpg*.

        Args:
            source_dir:  Directory containing C/C++ source files.
            output_cpg:  Destination path for the generated cpg.bin.

        Raises:
            JoernParseError: On non-zero exit code.
        """
        output_cpg.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            str(self.config.parse_bin),
            str(source_dir),
            "-o",
            str(output_cpg),
        ]
        logger.info("Running joern-parse — src={src}", src=source_dir)
        self._run(cmd, error_cls=JoernParseError, label="joern-parse")
        logger.info("joern-parse complete — cpg={cpg}", cpg=output_cpg)

    def export(
        self,
        cpg_path: Path,
        output_dir: Path,
        repr: str = "all",
        fmt: str = "graphson",
    ) -> None:
        """Run joern-export on *cpg_path*, writing graph files to *output_dir*.

        Args:
            cpg_path:   Path to the cpg.bin produced by :meth:`parse`.
            output_dir: Directory where the exported JSON files are written.
            repr:       CPG representation to export.
                        One of: ``"all"``, ``"ast"``, ``"cfg"``, ``"pdg"``.
            fmt:        Export format. Use ``"graphson"`` for JSON.

        Raises:
            JoernExportError: On non-zero exit code.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        cmd = [
            str(self.config.export_bin),
            str(cpg_path),
            "--repr",
            repr,
            "--format",
            fmt,
            "--out",
            str(output_dir),
        ]
        logger.info("Running joern-export — repr={repr} fmt={fmt}", repr=repr, fmt=fmt)
        self._run(cmd, error_cls=JoernExportError, label="joern-export")
        logger.info("joern-export complete — output={out}", out=output_dir)

    # ── Private helpers ────────────────────────────────────

    def _run(
        self,
        cmd: list[str],
        error_cls: type[JoernError],
        label: str,
    ) -> subprocess.CompletedProcess:
        """Execute *cmd*, log output, and raise *error_cls* on failure."""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.joern_timeout,
            )
        except subprocess.TimeoutExpired:
            raise error_cls(
                f"{label} timed out after {self.config.joern_timeout}s. "
                "Consider increasing JOERN_TIMEOUT in .env."
            )
        except FileNotFoundError as e:
            raise error_cls(f"Binary not found: {e}") from e

        # Log all output at DEBUG level
        if result.stdout:
            for line in result.stdout.splitlines():
                logger.debug("[{label}] {line}", label=label, line=line)
        if result.stderr:
            for line in result.stderr.splitlines():
                logger.debug("[{label}:err] {line}", label=label, line=line)

        if result.returncode != 0:
            snippet = (result.stderr or result.stdout or "")[-1000:]
            raise error_cls(
                f"{label} exited with code {result.returncode}.\n"
                f"Last output:\n{snippet}"
            )
        return result
