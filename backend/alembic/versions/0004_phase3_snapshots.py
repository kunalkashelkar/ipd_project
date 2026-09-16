"""Phase 3 — Source Snapshots, Source Files, Functions, and Repository Ingestion

Revision ID: 0004_phase3_snapshots_files_functions
Revises: 0003_phase2_sync_model_columns
Create Date: 2026-09-16 18:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0004_phase3_snapshots'
down_revision: Union[str, None] = '0003_phase2_sync_model_columns'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. projects: add archived_at
    op.add_column('projects', sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True))

    # 2. repositories: add disconnected_at
    op.add_column('repositories', sa.Column('disconnected_at', sa.DateTime(timezone=True), nullable=True))

    # 3. source_snapshots
    op.create_table(
        'source_snapshots',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('repository_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('repositories.id', ondelete='SET NULL'), nullable=True),
        sa.Column('repository_commit_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('repository_commits.id', ondelete='SET NULL'), nullable=True),
        sa.Column('source_type', sa.String(length=30), nullable=False),
        sa.Column('source_version', sa.String(length=100), nullable=True),
        sa.Column('content_hash', sa.String(length=64), nullable=False),
        sa.Column('artifact_uri', sa.String(length=1024), nullable=False),
        sa.Column('manifest_uri', sa.String(length=1024), nullable=True),
        sa.Column('status', sa.String(length=30), server_default='pending', nullable=False),
        sa.Column('file_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('total_bytes', sa.BigInteger(), server_default='0', nullable=False),
        sa.Column('detected_languages', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('preprocessing_version', sa.String(length=50), server_default='v1.0.0', nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('failure_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_source_snapshots_project_id', 'source_snapshots', ['project_id'])
    op.create_index('ix_source_snapshots_repository_id', 'source_snapshots', ['repository_id'])
    op.create_index('ix_source_snapshots_commit_id', 'source_snapshots', ['repository_commit_id'])
    op.create_index('ix_source_snapshots_source_type', 'source_snapshots', ['source_type'])
    op.create_index('ix_source_snapshots_status', 'source_snapshots', ['status'])
    op.create_index('ix_source_snapshots_content_hash', 'source_snapshots', ['content_hash'])

    # 4. source_files
    op.create_table(
        'source_files',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('source_snapshot_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('source_snapshots.id', ondelete='CASCADE'), nullable=False),
        sa.Column('relative_path', sa.String(length=1024), nullable=False),
        sa.Column('path_hash', sa.String(length=64), nullable=False),
        sa.Column('language', sa.String(length=50), nullable=True),
        sa.Column('size_bytes', sa.Integer(), server_default='0', nullable=False),
        sa.Column('content_hash', sa.String(length=64), nullable=False),
        sa.Column('original_artifact_uri', sa.String(length=1024), nullable=False),
        sa.Column('normalized_artifact_uri', sa.String(length=1024), nullable=True),
        sa.Column('token_artifact_uri', sa.String(length=1024), nullable=True),
        sa.Column('line_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('encoding', sa.String(length=30), server_default='utf-8', nullable=False),
        sa.Column('is_binary', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('is_generated', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('validation_status', sa.String(length=30), server_default='valid', nullable=False),
        sa.Column('preprocessing_status', sa.String(length=30), server_default='pending', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('source_snapshot_id', 'relative_path', name='uq_snapshot_file_relpath'),
    )
    op.create_index('ix_source_files_snapshot_id', 'source_files', ['source_snapshot_id'])
    op.create_index('ix_source_files_path_hash', 'source_files', ['path_hash'])
    op.create_index('ix_source_files_content_hash', 'source_files', ['content_hash'])
    op.create_index('ix_source_files_language', 'source_files', ['language'])

    # 5. functions
    op.create_table(
        'functions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('source_file_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('source_files.id', ondelete='CASCADE'), nullable=False),
        sa.Column('function_id', sa.String(length=128), nullable=False),
        sa.Column('qualified_name', sa.String(length=512), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('language', sa.String(length=50), nullable=True),
        sa.Column('start_line', sa.Integer(), nullable=False),
        sa.Column('end_line', sa.Integer(), nullable=False),
        sa.Column('start_byte', sa.Integer(), nullable=True),
        sa.Column('end_byte', sa.Integer(), nullable=True),
        sa.Column('signature', sa.Text(), nullable=True),
        sa.Column('original_content_hash', sa.String(length=64), nullable=False),
        sa.Column('normalized_content_hash', sa.String(length=64), nullable=False),
        sa.Column('token_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('duplicate_group_id', sa.String(length=64), nullable=True),
        sa.Column('extraction_status', sa.String(length=30), server_default='extracted', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_functions_source_file_id', 'functions', ['source_file_id'])
    op.create_index('ix_functions_function_id', 'functions', ['function_id'])
    op.create_index('ix_functions_name', 'functions', ['name'])
    op.create_index('ix_functions_normalized_hash', 'functions', ['normalized_content_hash'])
    op.create_index('ix_functions_duplicate_group_id', 'functions', ['duplicate_group_id'])

    # 6. scans: add source_snapshot_id foreign key
    op.add_column('scans', sa.Column('source_snapshot_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('source_snapshots.id', ondelete='SET NULL'), nullable=True))
    op.create_index('ix_scans_source_snapshot_id', 'scans', ['source_snapshot_id'])


def downgrade() -> None:
    # 6. scans: drop source_snapshot_id
    op.drop_index('ix_scans_source_snapshot_id', table_name='scans')
    op.drop_column('scans', 'source_snapshot_id')

    # 5. functions
    op.drop_table('functions')

    # 4. source_files
    op.drop_table('source_files')

    # 3. source_snapshots
    op.drop_table('source_snapshots')

    # 2. repositories
    op.drop_column('repositories', 'disconnected_at')

    # 1. projects
    op.drop_column('projects', 'archived_at')
