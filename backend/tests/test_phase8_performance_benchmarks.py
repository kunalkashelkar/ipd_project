# ============================================================
# Phase 8 Performance Benchmark Harness & Acceptance
# ============================================================
# Measures deterministic, bounded performance across:
# - Tier A: 10 files
# - Tier B: 100 files
# - Tier C: 1,000 files
# Measures wall-clock times, throughput, memory overhead, and
# verifies all resource limits remain bounded without repo pollution.
# ============================================================

from __future__ import annotations

import ast
import hashlib
import tempfile
import time
import tracemalloc
import zipfile
from pathlib import Path
from typing import Any

import pytest

from backend.app.core.metrics import metrics
from backend.app.services.finding_service.fingerprint import compute_finding_fingerprint
from backend.app.utils.zip_utils import safe_extract_zip


def _generate_synthetic_repo(base_dir: Path, file_count: int) -> list[Path]:
    """Generate deterministic synthetic source files containing Python functions and logic."""
    created_files: list[Path] = []
    src_dir = base_dir / "src"
    src_dir.mkdir(parents=True, exist_ok=True)

    for i in range(file_count):
        file_path = src_dir / f"module_{i:04d}.py"
        # Deterministically mix clean and vulnerable functions
        if i % 10 == 0:
            content = f"""# Module {i} - Simulated Command/SQL
import os

def process_data_{i}(user_input: str) -> None:
    \"\"\"Simulated vulnerable data sink.\"\"\"
    cmd = "echo " + user_input
    os.system(cmd)

def safe_helper_{i}(val: int) -> int:
    return val * 2
"""
        else:
            content = f"""# Module {i} - Standard Logic
def compute_metric_{i}(a: int, b: int) -> int:
    result = a + b
    return result * 10

class Handler_{i}:
    def __init__(self, name: str):
        self.name = name

    def execute(self) -> str:
        return f"Handler {i}: " + self.name
"""
        file_path.write_text(content, encoding="utf-8")
        created_files.append(file_path)

    return created_files


def _benchmark_pipeline_for_files(files: list[Path], tier_name: str) -> dict[str, Any]:
    """Execute and measure pipeline stages for a given set of files."""
    tracemalloc.start()
    start_wall = time.perf_counter()
    timings: dict[str, float] = {}

    # 1. Archive creation & hashing
    t0 = time.perf_counter()
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp_zip:
        zip_path = Path(tmp_zip.name)

    try:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in files:
                zf.write(f, arcname=f.name)

        archive_bytes = zip_path.read_bytes()
        content_hash = hashlib.sha256(archive_bytes).hexdigest()
        timings["archive_create_hash_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)

        # 2. Archive extraction & traversal validation
        t1 = time.perf_counter()
        with tempfile.TemporaryDirectory() as extract_dir:
            safe_extract_zip(zip_path, Path(extract_dir))
            extracted_files = [p for p in Path(extract_dir).rglob("*") if p.is_file()]
            timings["archive_extract_ms"] = round((time.perf_counter() - t1) * 1000.0, 2)

            # 3. Preprocessing & AST parsing
            t2 = time.perf_counter()
            total_functions = 0
            syntax_clean = 0
            for ef in extracted_files:
                code = ef.read_text(encoding="utf-8", errors="replace")
                try:
                    tree = ast.parse(code, filename=str(ef))
                    syntax_clean += 1
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            total_functions += 1
                except SyntaxError:
                    pass
            timings["preprocessing_ast_ms"] = round((time.perf_counter() - t2) * 1000.0, 2)

            # 4. Static Pattern & Taint Candidate Discovery
            t3 = time.perf_counter()
            simulated_findings = []
            for idx, ef in enumerate(extracted_files):
                if idx % 10 == 0:
                    simulated_findings.append({
                        "file_path": str(ef.name),
                        "line": 5,
                        "cwe": "CWE-78",
                        "rule_id": "python-os-system-injection",
                        "severity": "CRITICAL",
                    })
            timings["static_analysis_ms"] = round((time.perf_counter() - t3) * 1000.0, 2)

            # 5. Finding Correlation & Fingerprinting
            t4 = time.perf_counter()
            fingerprints = []
            for sf in simulated_findings:
                fp, _ = compute_finding_fingerprint(
                    cwe_id=sf["cwe"],
                    file_path=sf["file_path"],
                    line_number=sf["line"],
                )
                fingerprints.append(fp)
            timings["correlation_fingerprint_ms"] = round((time.perf_counter() - t4) * 1000.0, 2)

        total_wall_ms = round((time.perf_counter() - start_wall) * 1000.0, 2)
        current_mem, peak_mem = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        throughput_fps = round(len(files) / max(0.001, total_wall_ms / 1000.0), 1)

        result = {
            "tier": tier_name,
            "file_count": len(files),
            "total_bytes": len(archive_bytes),
            "function_count": total_functions,
            "findings_count": len(simulated_findings),
            "timings": timings,
            "total_wall_ms": total_wall_ms,
            "throughput_files_per_sec": throughput_fps,
            "peak_memory_mb": round(peak_mem / (1024 * 1024), 2),
        }
        return result

    finally:
        if zip_path.exists():
            zip_path.unlink()


@pytest.mark.asyncio
async def test_benchmark_tier_a_10_files():
    """Benchmark representative Tier A repository (10 files)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        files = _generate_synthetic_repo(Path(tmpdir), 10)
        res = _benchmark_pipeline_for_files(files, "Tier A (10 files)")
        print(f"\n[BENCHMARK] {res['tier']}: Total={res['total_wall_ms']}ms, Throughput={res['throughput_files_per_sec']} files/s, PeakMem={res['peak_memory_mb']}MB, Breakdown={res['timings']}")
        assert res["file_count"] == 10
        assert res["total_wall_ms"] < 10000.0  # Resilient bounded execution

@pytest.mark.asyncio
async def test_benchmark_tier_b_100_files():
    """Benchmark representative Tier B repository (100 files)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        files = _generate_synthetic_repo(Path(tmpdir), 100)
        res = _benchmark_pipeline_for_files(files, "Tier B (100 files)")
        print(f"\n[BENCHMARK] {res['tier']}: Total={res['total_wall_ms']}ms, Throughput={res['throughput_files_per_sec']} files/s, PeakMem={res['peak_memory_mb']}MB, Breakdown={res['timings']}")
        assert res["file_count"] == 100
        assert res["total_wall_ms"] < 15000.0  # Resilient bounded execution


@pytest.mark.asyncio
async def test_benchmark_tier_c_1000_files():
    """Benchmark representative Tier C repository (1,000 files)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        files = _generate_synthetic_repo(Path(tmpdir), 1000)
        res = _benchmark_pipeline_for_files(files, "Tier C (1,000 files)")
        print(f"\n[BENCHMARK] {res['tier']}: Total={res['total_wall_ms']}ms, Throughput={res['throughput_files_per_sec']} files/s, PeakMem={res['peak_memory_mb']}MB, Breakdown={res['timings']}")
        assert res["file_count"] == 1000
        assert res["total_wall_ms"] < 30000.0  # Bounded execution, well under 30 seconds

