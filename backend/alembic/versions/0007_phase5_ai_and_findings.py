"""Phase 5: AI predictions, finding domain, occurrences, lifecycle, assignments, comments, and suppressions

Revision ID: 0007_phase5_ai_and_findings
Revises: 0006_phase4_scan_pipeline
Create Date: 2026-09-17 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0007_phase5_ai_and_findings'
down_revision: Union[str, None] = '0006_phase4_scan_pipeline'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    # 1. ai_predictions table
    if 'ai_predictions' not in existing_tables:
        op.create_table(
            'ai_predictions',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column('scan_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('source_snapshot_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('source_file_id', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('function_id', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('file_path', sa.String(length=1024), nullable=False),
            sa.Column('function_name', sa.String(length=255), nullable=True),
            sa.Column('line_number', sa.Integer(), nullable=True),
            sa.Column('end_line', sa.Integer(), nullable=True),
            sa.Column('prediction', sa.String(length=50), nullable=False, server_default='VULNERABLE'),
            sa.Column('confidence', sa.Float(), nullable=False),
            sa.Column('cwe_id', sa.String(length=50), nullable=True),
            sa.Column('severity', sa.String(length=20), nullable=False),
            sa.Column('cvss_score', sa.Float(), nullable=True),
            sa.Column('evidence_json', postgresql.JSON(), nullable=True),
            sa.Column('provider', sa.String(length=100), nullable=False),
            sa.Column('model_name', sa.String(length=100), nullable=False),
            sa.Column('model_version', sa.String(length=50), nullable=False),
            sa.Column('input_schema_version', sa.String(length=50), nullable=False, server_default='v1.0.0'),
            sa.Column('output_schema_version', sa.String(length=50), nullable=False, server_default='v1.0.0'),
            sa.Column('generated_by_ai', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(['scan_id'], ['scans.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['source_snapshot_id'], ['source_snapshots.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['source_file_id'], ['source_files.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['function_id'], ['functions.id'], ondelete='SET NULL'),
        )
        op.create_index('ix_ai_predictions_scan_id', 'ai_predictions', ['scan_id'])
        op.create_index('ix_ai_predictions_source_snapshot_id', 'ai_predictions', ['source_snapshot_id'])
        op.create_index('ix_ai_predictions_source_file_id', 'ai_predictions', ['source_file_id'])
        op.create_index('ix_ai_predictions_function_id', 'ai_predictions', ['function_id'])
        op.create_index('ix_ai_predictions_cwe_id', 'ai_predictions', ['cwe_id'])
        op.create_index('ix_ai_predictions_provider', 'ai_predictions', ['provider'])

    # 2. findings table
    if 'findings' not in existing_tables:
        op.create_table(
            'findings',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('title', sa.String(length=255), nullable=False),
            sa.Column('vulnerability_type', sa.String(length=100), nullable=False),
            sa.Column('cwe_id', sa.String(length=50), nullable=True),
            sa.Column('severity', sa.String(length=20), nullable=False),
            sa.Column('cvss_score', sa.Float(), nullable=True),
            sa.Column('confidence', sa.Float(), nullable=False, server_default='0.0'),
            sa.Column('risk_score', sa.Float(), nullable=False, server_default='0.0'),
            sa.Column('risk_version', sa.String(length=20), nullable=False, server_default='v1.0'),
            sa.Column('status', sa.String(length=50), nullable=False, server_default='OPEN'),
            sa.Column('fingerprint', sa.String(length=64), nullable=False),
            sa.Column('fingerprint_version', sa.String(length=20), nullable=False, server_default='v1.0'),
            sa.Column('first_seen_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('fixed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
            sa.UniqueConstraint('project_id', 'fingerprint', name='uq_project_finding_fingerprint')
        )
        op.create_index('ix_findings_project_id', 'findings', ['project_id'])
        op.create_index('ix_findings_organization_id', 'findings', ['organization_id'])
        op.create_index('ix_findings_vulnerability_type', 'findings', ['vulnerability_type'])
        op.create_index('ix_findings_cwe_id', 'findings', ['cwe_id'])
        op.create_index('ix_findings_severity', 'findings', ['severity'])
        op.create_index('ix_findings_status', 'findings', ['status'])
        op.create_index('ix_findings_risk_score', 'findings', ['risk_score'])
        op.create_index('ix_findings_fingerprint', 'findings', ['fingerprint'])

    # 3. finding_occurrences table
    if 'finding_occurrences' not in existing_tables:
        op.create_table(
            'finding_occurrences',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column('finding_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('scan_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('source_snapshot_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('file_path', sa.String(length=1024), nullable=False),
            sa.Column('function_name', sa.String(length=255), nullable=True),
            sa.Column('start_line', sa.Integer(), nullable=True),
            sa.Column('end_line', sa.Integer(), nullable=True),
            sa.Column('location', postgresql.JSON(), nullable=True),
            sa.Column('ai_prediction_id', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('static_evidence_ref', postgresql.JSON(), nullable=True),
            sa.Column('taint_evidence_ref', postgresql.JSON(), nullable=True),
            sa.Column('graph_evidence_ref', postgresql.JSON(), nullable=True),
            sa.Column('confidence', sa.Float(), nullable=False, server_default='0.0'),
            sa.Column('severity', sa.String(length=20), nullable=False),
            sa.Column('observed_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(['finding_id'], ['findings.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['scan_id'], ['scans.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['source_snapshot_id'], ['source_snapshots.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['ai_prediction_id'], ['ai_predictions.id'], ondelete='SET NULL')
        )
        op.create_index('ix_finding_occurrences_finding_id', 'finding_occurrences', ['finding_id'])
        op.create_index('ix_finding_occurrences_scan_id', 'finding_occurrences', ['scan_id'])
        op.create_index('ix_finding_occurrences_source_snapshot_id', 'finding_occurrences', ['source_snapshot_id'])
        op.create_index('ix_finding_occurrences_ai_prediction_id', 'finding_occurrences', ['ai_prediction_id'])

    # 4. finding_status_history table
    if 'finding_status_history' not in existing_tables:
        op.create_table(
            'finding_status_history',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column('finding_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('previous_status', sa.String(length=50), nullable=True),
            sa.Column('new_status', sa.String(length=50), nullable=False),
            sa.Column('actor_id', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('reason', sa.Text(), nullable=True),
            sa.Column('change_metadata', postgresql.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(['finding_id'], ['findings.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ondelete='SET NULL')
        )
        op.create_index('ix_finding_status_history_finding_id', 'finding_status_history', ['finding_id'])
        op.create_index('ix_finding_status_history_actor_id', 'finding_status_history', ['actor_id'])

    # 5. finding_assignments table
    if 'finding_assignments' not in existing_tables:
        op.create_table(
            'finding_assignments',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column('finding_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('assigned_to_user_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('assigned_by_user_id', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('active', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(['finding_id'], ['findings.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['assigned_to_user_id'], ['users.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['assigned_by_user_id'], ['users.id'], ondelete='SET NULL')
        )
        op.create_index('ix_finding_assignments_finding_id', 'finding_assignments', ['finding_id'])
        op.create_index('ix_finding_assignments_assigned_to_user_id', 'finding_assignments', ['assigned_to_user_id'])

    # 6. finding_comments table
    if 'finding_comments' not in existing_tables:
        op.create_table(
            'finding_comments',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column('finding_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('author_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('content', sa.Text(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(['finding_id'], ['findings.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['author_id'], ['users.id'], ondelete='CASCADE')
        )
        op.create_index('ix_finding_comments_finding_id', 'finding_comments', ['finding_id'])
        op.create_index('ix_finding_comments_author_id', 'finding_comments', ['author_id'])

    # 7. finding_suppressions table
    if 'finding_suppressions' not in existing_tables:
        op.create_table(
            'finding_suppressions',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column('finding_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('actor_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('suppression_type', sa.String(length=50), nullable=False),
            sa.Column('reason', sa.Text(), nullable=False),
            sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('active', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(['finding_id'], ['findings.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ondelete='CASCADE')
        )
        op.create_index('ix_finding_suppressions_finding_id', 'finding_suppressions', ['finding_id'])
        op.create_index('ix_finding_suppressions_actor_id', 'finding_suppressions', ['actor_id'])


def downgrade() -> None:
    # Drop tables in reverse dependency order
    op.drop_table('finding_suppressions')
    op.drop_table('finding_comments')
    op.drop_table('finding_assignments')
    op.drop_table('finding_status_history')
    op.drop_table('finding_occurrences')
    op.drop_table('findings')
    op.drop_table('ai_predictions')
