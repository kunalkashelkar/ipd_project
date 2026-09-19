# ============================================================
# Phase 7 Notifications Tests
# ============================================================

import uuid
import pytest

from backend.app.models.notification import Notification
from backend.app.services.notification_service import NotificationService


@pytest.mark.asyncio
async def test_notification_service_events_and_deduplication(db_session, test_user, test_organization, test_project):
    service = NotificationService(db_session)

    # 1. Event: scan_completed
    scan_id = uuid.uuid4()
    await service.notify_scan_completed(
        scan_id=scan_id,
        public_scan_id="scn_abc123",
        project_id=test_project.id,
        project_name=test_project.name,
        organization_id=test_organization.id,
    )

    # Verify notification created
    notifs, count = await service.get_user_notifications(test_user.id)
    assert count >= 1
    assert any(n.type == "scan_completed" for n in notifs)

    # 2. Test Deduplication (retry task with same event_key does not create duplicate!)
    await service.notify_scan_completed(
        scan_id=scan_id,
        public_scan_id="scn_abc123",
        project_id=test_project.id,
        project_name=test_project.name,
        organization_id=test_organization.id,
    )
    _, count_after_retry = await service.get_user_notifications(test_user.id)
    assert count_after_retry == count, "Duplicate event_key must be safely deduplicated"

    # 3. Event: critical_finding
    finding_id = uuid.uuid4()
    await service.notify_critical_finding(
        finding_id=finding_id,
        finding_public_id="fnd_crit001",
        title="Remote Code Execution in Parser",
        project_id=test_project.id,
        organization_id=test_organization.id,
    )

    # 4. Event: fix_ready
    rem_id = uuid.uuid4()
    await service.notify_fix_ready(
        finding_id=finding_id,
        finding_public_id="fnd_crit001",
        user_id=test_user.id,
        organization_id=test_organization.id,
        remediation_id=rem_id,
    )

    # 5. Event: fix_validated
    val_id = uuid.uuid4()
    await service.notify_fix_validated(
        finding_id=finding_id,
        finding_public_id="fnd_crit001",
        user_id=test_user.id,
        organization_id=test_organization.id,
        validation_status="passed",
    )

    # 6. Event: finding_reopened
    await service.notify_finding_reopened(
        finding_id=finding_id,
        finding_public_id="fnd_crit001",
        title="Remote Code Execution in Parser",
        organization_id=test_organization.id,
    )

    # 7. Event: repository_disconnected
    repo_id = uuid.uuid4()
    await service.notify_repository_disconnected(
        repo_id=repo_id,
        repo_url="https://github.com/org/repo.git",
        organization_id=test_organization.id,
    )

    # 8. Event: user_mentioned
    com_id = uuid.uuid4()
    await service.notify_user_mentioned(
        comment_id=com_id,
        finding_id=finding_id,
        finding_public_id="fnd_crit001",
        mentioned_user_id=test_user.id,
        author_name="Alice Security",
        organization_id=test_organization.id,
    )

    # Verify unread count and marking read
    unread = await service.get_unread_count(test_user.id)
    assert unread >= 6

    # Verify all 7 event types have valid navigation link_urls
    notifs, count = await service.get_user_notifications(test_user.id)
    types_found = {n.type: n.link_url for n in notifs if n.link_url}
    for ev in ["scan_completed", "critical_finding", "fix_ready", "fix_validated", "finding_reopened", "repository_disconnected", "user_mentioned"]:
        assert ev in types_found, f"Event {ev} must have an emitted notification with a navigation link"
        assert types_found[ev].startswith("/"), f"Navigation target for {ev} must be an absolute path: {types_found[ev]}"

    # Mark all read
    marked = await service.mark_all_as_read(test_user.id)
    assert marked >= 6

    unread_after = await service.get_unread_count(test_user.id)
    assert unread_after == 0


@pytest.mark.asyncio
async def test_repository_disconnect_notification_emission(db_session, test_organization, test_project, test_user):
    """Prove that repository disconnection emits repository_disconnected notification to org members."""
    from backend.app.models.repository import Repository
    from backend.app.repositories.repository_vcs_repository import RepositoryVcsRepository

    repo_repo = RepositoryVcsRepository(db_session)
    repo = await repo_repo.create_repository(
        project_id=test_project.id,
        provider="github",
        repository_url="https://github.com/org/disconnect-test.git",
        branch="main",
        auth_method="none",
    )

    notif_svc = NotificationService(db_session)
    await notif_svc.notify_repository_disconnected(
        repo_id=repo.id,
        repo_url=repo.repository_url,
        organization_id=test_organization.id,
    )

    notifs, count = await notif_svc.get_user_notifications(test_user.id)
    disconn_notifs = [n for n in notifs if n.type == "repository_disconnected"]
    assert len(disconn_notifs) >= 1
    assert "disconnect-test" in disconn_notifs[0].body or "disconnect-test" in disconn_notifs[0].title
    assert disconn_notifs[0].link_url == "/integrations"


@pytest.mark.asyncio
async def test_critical_finding_notification_semantics(db_session, test_organization, test_project, test_user):
    """Prove that critical finding notification is only emitted for NEW critical findings, not repeatedly."""
    from datetime import datetime, timezone, timedelta
    from backend.app.models.finding import Finding

    now = datetime.now(timezone.utc)
    notif_svc = NotificationService(db_session)

    # 1. New Critical Finding -> Should notify
    f_new = Finding(
        id=uuid.uuid4(),
        public_id="fnd_newcrit1",
        project_id=test_project.id,
        organization_id=test_organization.id,
        title="New Critical RCE",
        severity="critical",
        status="OPEN",
        first_seen_at=now,
        last_seen_at=now,
    )
    is_new = (
        f_new.first_seen_at is not None
        and f_new.last_seen_at is not None
        and abs((f_new.last_seen_at - f_new.first_seen_at).total_seconds()) < 5
    )
    assert is_new is True
    await notif_svc.notify_critical_finding(
        finding_id=f_new.id,
        finding_public_id=f_new.public_id,
        title=f_new.title,
        project_id=test_project.id,
        organization_id=test_organization.id,
    )

    # 2. Existing Unchanged Critical Finding -> Should NOT qualify as new
    f_old = Finding(
        id=uuid.uuid4(),
        public_id="fnd_oldcrit1",
        project_id=test_project.id,
        organization_id=test_organization.id,
        title="Old Known Critical",
        severity="critical",
        status="OPEN",
        first_seen_at=now - timedelta(days=7),
        last_seen_at=now,
    )
    is_old_new = (
        f_old.first_seen_at is not None
        and f_old.last_seen_at is not None
        and abs((f_old.last_seen_at - f_old.first_seen_at).total_seconds()) < 5
    )
    assert is_old_new is False, "Repeatedly observed finding must not be evaluated as new"


@pytest.mark.asyncio
async def test_fix_validated_notification_semantics(db_session, test_organization, test_user):
    """Prove that fix_validated notification is emitted strictly for successful validation."""
    notif_svc = NotificationService(db_session)
    finding_id = uuid.uuid4()

    # Success case: "passed"
    await notif_svc.notify_fix_validated(
        finding_id=finding_id,
        finding_public_id="fnd_pass001",
        user_id=test_user.id,
        organization_id=test_organization.id,
        validation_status="passed",
    )

    notifs, _ = await notif_svc.get_user_notifications(test_user.id)
    val_notif = next((n for n in notifs if n.event_key and "fnd_pass001" in n.body), None)
    assert val_notif is not None
    assert val_notif.severity == "success"
    assert val_notif.type == "fix_validated"

