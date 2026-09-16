"""Sync remaining Phase 1/2 model columns to PostgreSQL

Revision ID: 0003_phase2_sync_model_columns
Revises: 0002_phase2_identity_org_rbac
Create Date: 2026-09-16 15:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0003_phase2_sync_model_columns'
down_revision: Union[str, None] = '0002_phase2_identity_org_rbac'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. scans
    op.add_column('scans', sa.Column('ai_model_version', sa.String(length=50), nullable=True))

    # 2. scan_logs
    op.add_column('scan_logs', sa.Column('metadata_json', postgresql.JSON(astext_type=sa.Text()), nullable=True))

    # 3. scan_results
    op.add_column('scan_results', sa.Column('cvss_score', sa.Float(), nullable=True))
    op.add_column('scan_results', sa.Column('model_name', sa.String(length=100), nullable=True))

    # 4. uploads
    op.add_column('uploads', sa.Column('file_count', sa.Integer(), server_default='0', nullable=True))
    op.add_column('uploads', sa.Column('language', sa.String(length=50), nullable=True))
    op.add_column('uploads', sa.Column('error_message', sa.Text(), nullable=True))
    op.add_column('uploads', sa.Column('metadata_json', postgresql.JSON(astext_type=sa.Text()), nullable=True))

    # 5. repositories
    op.add_column('repositories', sa.Column('repository_url', sa.String(length=1024), nullable=True))
    op.add_column('repositories', sa.Column('branch', sa.String(length=100), server_default='main', nullable=True))
    op.add_column('repositories', sa.Column('commit_sha', sa.String(length=64), nullable=True))
    op.add_column('repositories', sa.Column('auth_method', sa.String(length=50), nullable=True))
    op.add_column('repositories', sa.Column('status', sa.String(length=20), server_default='connected', nullable=False))


def downgrade() -> None:
    # 5. repositories
    op.drop_column('repositories', 'status')
    op.drop_column('repositories', 'auth_method')
    op.drop_column('repositories', 'commit_sha')
    op.drop_column('repositories', 'branch')
    op.drop_column('repositories', 'repository_url')

    # 4. uploads
    op.drop_column('uploads', 'metadata_json')
    op.drop_column('uploads', 'error_message')
    op.drop_column('uploads', 'language')
    op.drop_column('uploads', 'file_count')

    # 3. scan_results
    op.drop_column('scan_results', 'model_name')
    op.drop_column('scan_results', 'cvss_score')

    # 2. scan_logs
    op.drop_column('scan_logs', 'metadata_json')

    # 1. scans
    op.drop_column('scans', 'ai_model_version')
