# ============================================================
# Phase 7 CI/CD & Collaboration Tests
# ============================================================

import hashlib
import uuid
import pytest
from datetime import datetime, timezone

from backend.app.models.api_key import ApiKey
from backend.app.models.finding import Finding
from backend.app.models.organization import OrganizationMember
from backend.app.models.user import User
from backend.app.services.notification_service import NotificationService
try:
    from backend.cli.security_cli import SecurityCLI
except ImportError:
    from cli.security_cli import SecurityCLI


@pytest.mark.asyncio
async def test_ci_api_and_gate_evaluation(client, db_session, test_user, test_organization, test_project):
    # 1. Create active API key for test user
    raw_key = "vulnscan_test_apikey_1234567890abcdef"
    key_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
    api_key = ApiKey(
        id=uuid.uuid4(),
        user_id=test_user.id,
        organization_id=test_organization.id,
        name="CI Test Key",
        key_hash=key_hash,
        key_prefix="vulnscan_test",
        revoked_at=None,
    )
    db_session.add(api_key)
    await db_session.commit()

    headers = {"X-API-Key": raw_key}

    # 2. Trigger CI scan
    trigger_resp = await client.post(
        "/api/v1/ci/scans",
        json={
            "project_id": test_project.public_id,
            "branch": "main",
            "commit_sha": "ci_commit_sha_123",
        },
        headers=headers,
    )
    assert trigger_resp.status_code == 202
    scan_id = trigger_resp.json()["data"]["scan_id"]
    assert scan_id.startswith("scn_")

    # 3. Check CI scan status
    status_resp = await client.get(f"/api/v1/ci/scans/{scan_id}", headers=headers)
    assert status_resp.status_code == 200
    assert status_resp.json()["data"]["status"] == "queued"

    # 4. Check CI gate
    gate_resp = await client.get(f"/api/v1/ci/scans/{scan_id}/gate", headers=headers)
    assert gate_resp.status_code == 200
    assert gate_resp.json()["data"]["exit_code"] in (0, 1, 2)


@pytest.mark.asyncio
async def test_collaboration_assignment_mentions_and_activity(
    client, db_session, test_user, test_organization, test_project
):
    # Create second user in same org
    user2 = User(
        id=uuid.uuid4(),
        email="bob@example.com",
        name="Bob Engineer",
        password_hash="fake_hash",
        status="active",
        is_verified=True,
    )
    db_session.add(user2)
    await db_session.commit()

    member2 = OrganizationMember(
        id=uuid.uuid4(),
        organization_id=test_organization.id,
        user_id=user2.id,
        role_id=(await db_session.execute(
            OrganizationMember.__table__.select().where(OrganizationMember.user_id == test_user.id)
        )).first().role_id,
        status="active",
    )
    db_session.add(member2)
    await db_session.commit()

    # Create finding
    now = datetime.now(timezone.utc)
    finding = Finding(
        id=uuid.uuid4(),
        project_id=test_project.id,
        organization_id=test_organization.id,
        title="Path Traversal in Upload",
        vulnerability_type="PATH_TRAVERSAL",
        severity="high",
        status="OPEN",
        risk_score=75.0,
        fingerprint="fp_collab_001",
        first_seen_at=now,
        last_seen_at=now,
    )
    db_session.add(finding)
    await db_session.commit()

    from backend.app.core.security import create_access_token
    token = create_access_token({"sub": str(test_user.id)})
    auth_headers = {
        "Authorization": f"Bearer {token}",
        "X-Organization-ID": str(test_organization.id),
    }

    # 1. Assign finding to Bob
    assign_resp = await client.post(
        f"/api/v1/findings/{finding.id}/assign",
        json={"user_id": str(user2.id)},
        headers=auth_headers,
    )
    assert assign_resp.status_code == 200

    # Verify Bob received an in-app notification
    notif_svc = NotificationService(db_session)
    bob_notifs, bob_count = await notif_svc.get_user_notifications(user2.id)
    assert bob_count >= 1
    assert any(n.type == "finding_assigned" for n in bob_notifs)

    # 2. Add comment with @mention of Bob
    comment_resp = await client.post(
        f"/api/v1/findings/{finding.id}/comments",
        json={"content": "Hey @bob, please review this upload sanitization."},
        headers=auth_headers,
    )
    assert comment_resp.status_code == 201

    # Verify Bob received mention notification
    bob_notifs2, bob_count2 = await notif_svc.get_user_notifications(user2.id)
    assert any(n.type == "user_mentioned" for n in bob_notifs2)

    # 3. Retrieve activity history
    activity_resp = await client.get(
        f"/api/v1/findings/{finding.id}/activity",
        headers=auth_headers,
    )
    assert activity_resp.status_code == 200
    activities = activity_resp.json()["data"]
    assert len(activities) >= 2  # assignment and comment
    types = [a["activity_type"] for a in activities]
    assert "assignment" in types
    assert "comment" in types
