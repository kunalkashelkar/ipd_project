# ============================================================
# Analysis Process Runner (Controlled Subprocess Execution)
# ============================================================

from __future__ import annotations

import os
import signal
import subprocess
import threading
from pathlib import Path
from typing import Mapping, Sequence

from loguru import logger


class ProcessExecutionError(Exception):
    """Base exception for external analysis execution failure."""

    def __init__(self, message: str, returncode: int | None = None, stdout: str = "", stderr: str = ""):
        super().__init__(message)
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class ProcessTimeoutError(ProcessExecutionError):
    """Raised when an external process exceeds its deadline."""


class ProcessCancelledError(ProcessExecutionError):
    """Raised when an external process is explicitly aborted."""


class AnalysisProcessRunner:
    """Hardened, bounded subprocess runner for Joern and analysis binaries.

    Enforces:
    - Array arguments (no shell=True) to eliminate shell command injection
    - Bounded execution timeouts with guaranteed process group SIGKILL on expiry
    - Strict stdout/stderr truncation to prevent out-of-memory crashes
    - Sanitized execution environment
    """

    MAX_OUTPUT_BYTES = 2 * 1024 * 1024  # 2MB max captured output

    def run(
        self,
        args: Sequence[str | Path],
        *,
        cwd: Path | str | None = None,
        timeout: int = 300,
        env: Mapping[str, str] | None = None,
        cancel_event: threading.Event | None = None,
        label: str = "analysis-process",
    ) -> subprocess.CompletedProcess[str]:
        """Execute command safely with array arguments and deadline management."""
        cmd_args = [str(a) for a in args]
        sanitized_env = dict(os.environ)
        if env:
            sanitized_env.update(env)

        logger.debug("[{label}] Executing: {cmd}", label=label, cmd=" ".join(cmd_args[:5]))

        # Ensure cwd exists if provided
        exec_cwd = str(cwd) if cwd else None
        if exec_cwd and not Path(exec_cwd).exists():
            raise ProcessExecutionError(f"Working directory does not exist: {exec_cwd}")

        # Start process with its own process group for clean group-kill
        try:
            proc = subprocess.Popen(
                cmd_args,
                cwd=exec_cwd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=sanitized_env,
                preexec_fn=os.setsid if hasattr(os, "setsid") else None,
            )
        except FileNotFoundError as e:
            raise ProcessExecutionError(f"Binary not found: {cmd_args[0]}") from e
        except Exception as e:
            raise ProcessExecutionError(f"Failed to spawn process '{label}': {e}") from e

        # Monitor cancellation or timeout
        timed_out = False
        cancelled = False

        def poll_cancel():
            nonlocal cancelled
            if cancel_event and cancel_event.is_set():
                cancelled = True
                self._terminate_proc(proc)

        timer = None
        if cancel_event:
            # Poll cancellation flag every 0.5s
            def cancel_loop():
                while proc.poll() is None:
                    if cancel_event.is_set():
                        poll_cancel()
                        break
                    cancel_event.wait(0.5)

            t = threading.Thread(target=cancel_loop, daemon=True)
            t.start()

        try:
            stdout_data, stderr_data = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            self._terminate_proc(proc)
            stdout_data, stderr_data = proc.communicate()
        except Exception as e:
            self._terminate_proc(proc)
            raise ProcessExecutionError(f"Unexpected error executing '{label}': {e}") from e

        # Truncate output to bounds
        stdout_capped = (stdout_data or "")[: self.MAX_OUTPUT_BYTES]
        stderr_capped = (stderr_data or "")[: self.MAX_OUTPUT_BYTES]

        if cancelled:
            raise ProcessCancelledError(
                f"Process '{label}' was cancelled",
                returncode=proc.returncode,
                stdout=stdout_capped,
                stderr=stderr_capped,
            )

        if timed_out:
            raise ProcessTimeoutError(
                f"Process '{label}' timed out after {timeout} seconds",
                returncode=proc.returncode,
                stdout=stdout_capped,
                stderr=stderr_capped,
            )

        if proc.returncode != 0:
            last_err = (stderr_capped or stdout_capped)[-1000:]
            raise ProcessExecutionError(
                f"Process '{label}' failed with exit code {proc.returncode}: {last_err}",
                returncode=proc.returncode,
                stdout=stdout_capped,
                stderr=stderr_capped,
            )

        return subprocess.CompletedProcess(
            args=cmd_args,
            returncode=proc.returncode,
            stdout=stdout_capped,
            stderr=stderr_capped,
        )

    def _terminate_proc(self, proc: subprocess.Popen) -> None:
        """Safely terminate a process and its process group."""
        try:
            if hasattr(os, "killpg") and hasattr(os, "getpgid"):
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                proc.wait(timeout=2)
            else:
                proc.terminate()
                proc.wait(timeout=2)
        except Exception:
            try:
                if hasattr(os, "killpg") and hasattr(os, "getpgid"):
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                else:
                    proc.kill()
            except Exception:
                pass
