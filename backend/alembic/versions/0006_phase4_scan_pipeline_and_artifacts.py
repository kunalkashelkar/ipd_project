"""Phase 4: Scan pipeline lifecycle, stage history, and analysis artifacts

Revision ID: 0006_phase4_scan_pipeline_and_artifacts
Revises: 0005_reconcile_repository_schema
Create Date: 2026-09-17 02:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0006_phase4_scan_pipeline'
down_revision: Union[str, None] = '0005_reconcile_repository_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    scan_cols = {col['name'] for col in inspector.get_columns('scans')}

    # 1. Update scans table with lifecycle, attempt, timeout, and diagnostic fields
    if 'organization_id' not in scan_cols:
        op.add_column('scans', sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=True))
        op.create_foreign_key(
            'fk_scans_organization_id', 'scans', 'organizations',
            ['organization_id'], ['id'], ondelete='CASCADE'
        )
        op.create_index('ix_scans_organization_id', 'scans', ['organization_id'])

        # Backfill organization_id from projects
        op.execute(
            """
            UPDATE scans s
            SET organization_id = p.organization_id
            FROM projects p
            WHERE s.project_id = p.id AND s.organization_id IS NULL;
            """
        )

    if 'stage_attempt' not in scan_cols:
        op.add_column('scans', sa.Column('stage_attempt', sa.Integer(), server_default='1', nullable=False))

    if 'retry_count' not in scan_cols:
        op.add_column('scans', sa.Column('retry_count', sa.Integer(), server_default='0', nullable=False))

    if 'worker_id' not in scan_cols:
        op.add_column('scans', sa.Column('worker_id', sa.String(length=100), nullable=True))

    if 'heartbeat_at' not in scan_cols:
        op.add_column('scans', sa.Column('heartbeat_at', sa.DateTime(timezone=True), nullable=True))

    if 'timeout_seconds' not in scan_cols:
        op.add_column('scans', sa.Column('timeout_seconds', sa.Integer(), server_default='1800', nullable=False))

    if 'cancelled_at' not in scan_cols:
        op.add_column('scans', sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True))

    if 'failure_code' not in scan_cols:
        op.add_column('scans', sa.Column('failure_code', sa.String(length=50), nullable=True))

    if 'failure_reason' not in scan_cols:
        op.add_column('scans', sa.Column('failure_reason', sa.Text(), nullable=True))

    if 'config' not in scan_cols:
        op.add_column('scans', sa.Column('config', postgresql.JSON(astext_type=sa.Text()), nullable=True))

    if 'idempotency_key' not in scan_cols:
        op.add_column('scans', sa.Column('idempotency_key', sa.String(length=128), nullable=True))
        op.create_index('ix_scans_idempotency_key', 'scans', ['idempotency_key'])

    existing_indices = {ix['name'] for ix in inspector.get_indexes('scans')}
    if 'ix_scans_current_stage' not in existing_indices:
        op.create_index('ix_scans_current_stage', 'scans', ['current_stage'])
    if 'ix_scans_status' not in existing_indices:
        op.create_index('ix_scans_status', 'scans', ['status'])

    # 2. Create scan_stage_runs table
    tables = inspector.get_table_names()
    if 'scan_stage_runs' not in tables:
        op.create_table(
            'scan_stage_runs',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column('scan_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('stage', sa.String(length=50), nullable=False),
            sa.Column('attempt', sa.Integer(), server_default='1', nullable=False),
            sa.Column('status', sa.String(length=30), server_default='pending', nullable=False),
            sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('duration_seconds', sa.Float(), nullable=True),
            sa.Column('worker_id', sa.String(length=100), nullable=True),
            sa.Column('error_code', sa.String(length=50), nullable=True),
            sa.Column('error_message', sa.Text(), nullable=True),
            sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(['scan_id'], ['scans.id'], ondelete='CASCADE'),
            sa.UniqueConstraint('scan_id', 'stage', 'attempt', name='uq_scan_stage_attempt')
        )
        op.create_index('ix_scan_stage_runs_scan_id', 'scan_stage_runs', ['scan_id'])
        op.create_index('ix_scan_stage_runs_stage', 'scan_stage_runs', ['stage'])

    # 3. Create scan_events table
    if 'scan_events' not in tables:
        op.create_table(
            'scan_events',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column('scan_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('event_type', sa.String(length=50), nullable=False),
            sa.Column('stage', sa.String(length=50), nullable=True),
            sa.Column('payload', postgresql.JSON(astext_type=sa.Text()), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(['scan_id'], ['scans.id'], ondelete='CASCADE')
        )
        op.create_index('ix_scan_events_scan_id', 'scan_events', ['scan_id'])
        op.create_index('ix_scan_events_event_type', 'scan_events', ['event_type'])

    # 4. Create analysis_artifacts table
    if 'analysis_artifacts' not in tables:
        op.create_table(
            'analysis_artifacts',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column('scan_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('source_snapshot_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('artifact_type', sa.String(length=50), nullable=False),
            sa.Column('schema_version', sa.String(length=20), server_default='1.0.0', nullable=False),
            sa.Column('artifact_uri', sa.String(length=1024), nullable=False),
            sa.Column('content_hash', sa.String(length=64), nullable=False),
            sa.Column('size_bytes', sa.BigInteger(), server_default='0', nullable=False),
            sa.Column('status', sa.String(length=30), server_default='ready', nullable=False),
            sa.Column('tool_name', sa.String(length=100), nullable=True),
            sa.Column('tool_version', sa.String(length=50), nullable=True),
            sa.Column('config_hash', sa.String(length=64), nullable=True),
            sa.Column('node_count', sa.Integer(), server_default='0', nullable=False),
            sa.Column('edge_count', sa.Integer(), server_default='0', nullable=False),
            sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('error_message', sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(['scan_id'], ['scans.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['source_snapshot_id'], ['source_snapshots.id'], ondelete='CASCADE'),
            sa.UniqueConstraint('scan_id', 'artifact_type', name='uq_scan_artifact_type')
        )
        op.create_index('ix_analysis_artifacts_scan_id', 'analysis_artifacts', ['scan_id'])
        op.create_index('ix_analysis_artifacts_source_snapshot_id', 'analysis_artifacts', ['source_snapshot_id'])
        op.create_index('ix_analysis_artifacts_artifact_type', 'analysis_artifacts', ['artifact_type'])
        op.create_index('ix_analysis_artifacts_content_hash', 'analysis_artifacts', ['content_hash'])
        op.create_index('ix_analysis_artifacts_status', 'analysis_artifacts', ['status'])


def downgrade() -> None:
    # 1. Drop analysis_artifacts table
    op.drop_table('analysis_artifacts')

    # 2. Drop scan_events table
    op.drop_table('scan_events')

    # 3. Drop scan_stage_runs table
    op.drop_table('scan_stage_runs')

    # 4. Remove added columns from scans table
    op.drop_index('ix_scans_idempotency_key', table_name='scans')
    op.drop_index('ix_scans_organization_id', table_name='scans')
    op.drop_constraint('fk_scans_organization_id', 'scans', type_='foreignkey')

    op.drop_column('scans', 'idempotency_key')
    op.drop_column('scans', 'config')
    op.drop_column('scans', 'failure_reason')
    op.drop_column('scans', 'failure_code')
    op.drop_column('scans', 'cancelled_at')
    op.drop_column('scans', 'timeout_seconds')
    op.drop_column('scans', 'heartbeat_at')
    op.drop_column('scans', 'worker_id')
    op.drop_column('scans', 'retry_count')
    op.drop_column('scans', 'stage_attempt')
    op.drop_column('scans', 'organization_id')
