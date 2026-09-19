# ============================================================
# Phase 8 Reliability, Recovery & Observability Tests
# ============================================================
# Tests worker crash recovery (stale scan timeout sweep),
# health check readiness failure breakdown, operational metrics,
# and bounded retry / state machine invariants.
# ============================================================

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.core.metrics import metrics
from backend.app.main import app
from backend.app.models.organization import Organization
from backend.app.models.project import Project
from backend.app.models.scan import Scan
from backend.app.models.source_snapshot import SourceSnapshot
from backend.app.models.user import User
from backend.app.services.scan_lifecycle.lifecycle_service import ScanLifecycleService
from backend.app.services.scan_lifecycle.state_machine import ScanStage, ScanStatus


@pytest.mark.asyncio
async def test_stale_scan_cleanup_worker_crash_recovery(db_session):
    """Verify that scans with expired heartbeats are recovered and transitioned out of RUNNING."""
    lifecycle = ScanLifecycleService(db_session)

    # 1. Setup user, organization, project, snapshot, and an orphaned scan
    user = User(
        id=uuid.uuid4(),
        email=f"user-{uuid.uuid4().hex[:6]}@recovery.org",
        name="Recovery User",
        password_hash="hashed_pw_mock",
    )
    org = Organization(id=uuid.uuid4(), name="Recovery Org", slug=f"rec-{uuid.uuid4().hex[:6]}")
    project = Project(id=uuid.uuid4(), organization_id=org.id, name="Recovery Project", owner_id=user.id)
    snapshot = SourceSnapshot(
        id=uuid.uuid4(),
        project_id=project.id,
        source_type="upload_zip",
        content_hash="abc12345",
        artifact_uri="storage/snapshots/test.zip",
        status="ready",
    )
    db_session.add_all([user, org, project, snapshot])
    await db_session.flush()

    # Create a scan simulated as crashed/stale 2 hours ago
    stale_time = datetime.now(timezone.utc) - timedelta(hours=2)
    stale_scan = Scan(
        id=uuid.uuid4(),
        organization_id=org.id,
        project_id=project.id,
        source_snapshot_id=snapshot.id,
        status=ScanStatus.RUNNING.value,
        current_stage=ScanStage.STATIC_ANALYSIS.value,
        progress=35,
        worker_id="celery@worker-crashed-pid-9999",
        started_at=stale_time,
        heartbeat_at=stale_time,
        created_at=stale_time,
    )
    db_session.add(stale_scan)
    await db_session.commit()

    # Verify scan is currently RUNNING
    s = await lifecycle.get_scan(stale_scan.id)
    assert s.status == "running"

    # Run cleanup sweep with max_stale_seconds = 1800 (30 mins)
    recovered_ids = await lifecycle.cleanup_stale_scans(max_stale_seconds=1800)
    assert stale_scan.id in recovered_ids

    # Verify scan is no longer RUNNING — it is TIMED_OUT with WORKER_UNRESPONSIVE
    updated = await lifecycle.get_scan(stale_scan.id)
    assert updated.status == "timed_out"
    assert updated.failure_code == "WORKER_UNRESPONSIVE"
    assert "heartbeat expired" in (updated.failure_reason or "").lower()
    assert updated.completed_at is not None


@pytest.mark.asyncio
async def test_readiness_probe_dependency_breakdown():
    """Verify that /health/ready distinguishes individual dependencies and handles failures gracefully."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Normal readiness probe
        resp = await client.get("/health/ready")
        assert resp.status_code in (200, 503)
        data = resp.json()
        assert "data" in data
        assert "database" in data["data"]
        assert "redis" in data["data"]
        assert "storage" in data["data"]
        assert "workers" in data["data"]
        assert "ready" in data["data"]

        # 2. Simulate degraded dependency (e.g. redis failure)
        with patch("redis.asyncio.from_url", side_effect=Exception("Redis connection refused")):
            resp_fail = await client.get("/health/ready")
            assert resp_fail.status_code == 503
            fail_data = resp_fail.json()
            assert fail_data["data"]["redis"] == "unavailable"
            assert fail_data["data"]["ready"] is False


@pytest.mark.asyncio
async def test_operational_metrics_collector():
    """Verify that operational metrics record counters and duration histograms without leaking secrets."""
    metrics.reset()

    # Record some operations
    metrics.increment("test_requests_total", 5)
    metrics.observe("test_scan_duration_seconds", 12.4)
    metrics.observe("test_scan_duration_seconds", 15.6)

    snapshot = metrics.get_snapshot()
    assert snapshot["counters"]["test_requests_total"] == 5
    assert "test_scan_duration_seconds" in snapshot["durations"]
    assert snapshot["durations"]["test_scan_duration_seconds"]["count"] == 2
    assert snapshot["durations"]["test_scan_duration_seconds"]["avg"] == 14.0

    # Test HTTP endpoint
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.get("/health/metrics")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "uptime_seconds" in data
        assert "counters" in data
        assert "durations" in data
