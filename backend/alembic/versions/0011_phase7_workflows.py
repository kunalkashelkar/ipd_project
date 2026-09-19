"""Phase 7 product workflows: Reports, ReportFiles, Notifications, SecurityGates, PRSecurityResults, WebhookDeliveries

Revision ID: 0011_phase7_workflows
Revises: 0010_finding_public_id
Create Date: 2026-09-18 12:00:00.000000

"""
from typing import Sequence, Union
import secrets

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON, UUID


# revision identifiers, used by Alembic.
revision: str = '0011_phase7_workflows'
down_revision: Union[str, None] = '0010_finding_public_id'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyz"


def _generate_id(prefix: str) -> str:
    return f"{prefix}_{''.join(secrets.choice(ALPHABET) for _ in range(12))}"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    # ---------------------------------------------------------
    # 1. Enhance reports table
    # ---------------------------------------------------------
    if "reports" in existing_tables:
        cols = {c["name"] for c in inspector.get_columns("reports")}
        if "organization_id" not in cols:
            op.add_column("reports", sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True))
            op.create_index("ix_reports_organization_id", "reports", ["organization_id"])
        if "project_id" not in cols:
            op.add_column("reports", sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=True))
            op.create_index("ix_reports_project_id", "reports", ["project_id"])
        if "created_by" not in cols:
            op.add_column("reports", sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True))
            op.create_index("ix_reports_created_by", "reports", ["created_by"])
        if "report_type" not in cols:
            op.add_column("reports", sa.Column("report_type", sa.String(50), nullable=False, server_default="security"))
        if "config" not in cols:
            op.add_column("reports", sa.Column("config", JSON, nullable=True))

        # Backfill organization_id and project_id from scan if empty
        bind.execute(sa.text("""
            UPDATE reports r
            SET project_id = s.project_id,
                organization_id = p.organization_id
            FROM scans s
            JOIN projects p ON s.project_id = p.id
            WHERE r.scan_id = s.id AND (r.project_id IS NULL OR r.organization_id IS NULL)
        """))

    # ---------------------------------------------------------
    # 2. Create report_files table
    # ---------------------------------------------------------
    if "report_files" not in existing_tables:
        op.create_table(
            "report_files",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("report_id", UUID(as_uuid=True), sa.ForeignKey("reports.id", ondelete="CASCADE"), nullable=False),
            sa.Column("format", sa.String(10), nullable=False),
            sa.Column("storage_key", sa.String(1024), nullable=False),
            sa.Column("content_type", sa.String(100), nullable=False),
            sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("checksum_sha256", sa.String(64), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_report_files_report_id", "report_files", ["report_id"])

    # ---------------------------------------------------------
    # 3. Enhance notifications table
    # ---------------------------------------------------------
    if "notifications" in existing_tables:
        cols = {c["name"] for c in inspector.get_columns("notifications")}
        if "public_id" not in cols:
            op.add_column("notifications", sa.Column("public_id", sa.String(32), nullable=True))
            
            # Backfill public_id for notifications
            t_notif = sa.Table(
                "notifications",
                sa.MetaData(),
                sa.Column("id", UUID(as_uuid=True), primary_key=True),
                sa.Column("public_id", sa.String(32)),
            )
            rows = bind.execute(sa.select(t_notif.c.id).where(t_notif.c.public_id.is_(None))).fetchall()
            assigned = set()
            for (row_id,) in rows:
                new_pid = _generate_id("ntf")
                while new_pid in assigned:
                    new_pid = _generate_id("ntf")
                assigned.add(new_pid)
                bind.execute(sa.update(t_notif).where(t_notif.c.id == row_id).values(public_id=new_pid))
            
            op.alter_column("notifications", "public_id", nullable=False)
            op.create_index("ix_notifications_public_id", "notifications", ["public_id"], unique=True)

        if "organization_id" not in cols:
            op.add_column("notifications", sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True))
            op.create_index("ix_notifications_organization_id", "notifications", ["organization_id"])
        if "severity" not in cols:
            op.add_column("notifications", sa.Column("severity", sa.String(20), nullable=False, server_default="info"))
        if "link_url" not in cols:
            op.add_column("notifications", sa.Column("link_url", sa.String(512), nullable=True))
        if "event_key" not in cols:
            op.add_column("notifications", sa.Column("event_key", sa.String(128), nullable=True))
            op.create_index("ix_notifications_event_key", "notifications", ["event_key"])

    # ---------------------------------------------------------
    # 4. Create security_gate_policies table
    # ---------------------------------------------------------
    if "security_gate_policies" not in existing_tables:
        op.create_table(
            "security_gate_policies",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
            sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
            sa.Column("name", sa.String(100), nullable=False, server_default="Default Security Gate"),
            sa.Column("version", sa.String(20), nullable=False, server_default="v1.0.0"),
            sa.Column("block_new_critical", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("block_new_high", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("block_secrets", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("cvss_threshold", sa.Float(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint("project_id", name="uq_project_security_gate_policy"),
        )
        op.create_index("ix_security_gate_policies_project_id", "security_gate_policies", ["project_id"])
        op.create_index("ix_security_gate_policies_organization_id", "security_gate_policies", ["organization_id"])

    # ---------------------------------------------------------
    # 5. Create pr_security_results table
    # ---------------------------------------------------------
    if "pr_security_results" not in existing_tables:
        op.create_table(
            "pr_security_results",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("public_id", sa.String(32), nullable=False),
            sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
            sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
            sa.Column("repository_id", UUID(as_uuid=True), sa.ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False),
            sa.Column("pull_request_number", sa.Integer(), nullable=False),
            sa.Column("pr_title", sa.String(255), nullable=True),
            sa.Column("pr_head_sha", sa.String(64), nullable=False),
            sa.Column("pr_base_sha", sa.String(64), nullable=True),
            sa.Column("pr_branch", sa.String(100), nullable=True),
            sa.Column("baseline_scan_id", UUID(as_uuid=True), sa.ForeignKey("scans.id", ondelete="SET NULL"), nullable=True),
            sa.Column("pr_scan_id", UUID(as_uuid=True), sa.ForeignKey("scans.id", ondelete="SET NULL"), nullable=True),
            sa.Column("existing_findings_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("new_findings_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("fixed_findings_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("gate_result", sa.String(30), nullable=False, server_default="QUEUED"),
            sa.Column("gate_policy_version", sa.String(20), nullable=False, server_default="v1.0.0"),
            sa.Column("gate_details", JSON, nullable=True),
            sa.Column("github_check_run_id", sa.String(100), nullable=True),
            sa.Column("status", sa.String(30), nullable=False, server_default="QUEUED"),
            sa.Column("failure_reason", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_pr_security_results_public_id", "pr_security_results", ["public_id"], unique=True)
        op.create_index("ix_pr_security_results_organization_id", "pr_security_results", ["organization_id"])
        op.create_index("ix_pr_security_results_project_id", "pr_security_results", ["project_id"])
        op.create_index("ix_pr_security_results_repository_id", "pr_security_results", ["repository_id"])
        op.create_index("ix_pr_security_results_pr_head_sha", "pr_security_results", ["pr_head_sha"])

    # ---------------------------------------------------------
    # 6. Create webhook_deliveries table
    # ---------------------------------------------------------
    if "webhook_deliveries" not in existing_tables:
        op.create_table(
            "webhook_deliveries",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("delivery_id", sa.String(64), nullable=False),
            sa.Column("event_type", sa.String(50), nullable=False),
            sa.Column("repository_id", UUID(as_uuid=True), sa.ForeignKey("repositories.id", ondelete="SET NULL"), nullable=True),
            sa.Column("payload_hash", sa.String(64), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="processed"),
            sa.Column("processed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_webhook_deliveries_delivery_id", "webhook_deliveries", ["delivery_id"], unique=True)
        op.create_index("ix_webhook_deliveries_repository_id", "webhook_deliveries", ["repository_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "webhook_deliveries" in existing_tables:
        op.drop_table("webhook_deliveries")

    if "pr_security_results" in existing_tables:
        op.drop_table("pr_security_results")

    if "security_gate_policies" in existing_tables:
        op.drop_table("security_gate_policies")

    if "report_files" in existing_tables:
        op.drop_table("report_files")

    if "notifications" in existing_tables:
        cols = {c["name"] for c in inspector.get_columns("notifications")}
        if "event_key" in cols:
            op.drop_index("ix_notifications_event_key", table_name="notifications")
            op.drop_column("notifications", "event_key")
        if "link_url" in cols:
            op.drop_column("notifications", "link_url")
        if "severity" in cols:
            op.drop_column("notifications", "severity")
        if "organization_id" in cols:
            op.drop_index("ix_notifications_organization_id", table_name="notifications")
            op.drop_column("notifications", "organization_id")
        if "public_id" in cols:
            op.drop_index("ix_notifications_public_id", table_name="notifications")
            op.drop_column("notifications", "public_id")

    if "reports" in existing_tables:
        cols = {c["name"] for c in inspector.get_columns("reports")}
        if "config" in cols:
            op.drop_column("reports", "config")
        if "report_type" in cols:
            op.drop_column("reports", "report_type")
        if "created_by" in cols:
            op.drop_index("ix_reports_created_by", table_name="reports")
            op.drop_column("reports", "created_by")
        if "project_id" in cols:
            op.drop_index("ix_reports_project_id", table_name="reports")
            op.drop_column("reports", "project_id")
        if "organization_id" in cols:
            op.drop_index("ix_reports_organization_id", table_name="reports")
            op.drop_column("reports", "organization_id")
