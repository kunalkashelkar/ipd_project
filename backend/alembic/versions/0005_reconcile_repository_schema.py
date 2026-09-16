"""Reconcile repository schema: canonical repository_url and legacy column cleanup

Revision ID: 0005_reconcile_repository_schema
Revises: 0004_phase3_snapshots
Create Date: 2026-09-17 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0005_reconcile_repository_schema'
down_revision: Union[str, None] = '0004_phase3_snapshots'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col['name'] for col in inspector.get_columns('repositories')}

    # 1. Ensure canonical repository_url exists
    if 'repository_url' not in columns:
        op.add_column('repositories', sa.Column('repository_url', sa.String(length=1024), nullable=True))
        columns.add('repository_url')

    # 2. Data migration from legacy repo_url -> repository_url
    if 'repo_url' in columns:
        bind.execute(sa.text(
            "UPDATE repositories SET repository_url = repo_url WHERE repository_url IS NULL AND repo_url IS NOT NULL"
        ))
        op.drop_column('repositories', 'repo_url')

    # 3. Data migration from legacy default_branch -> branch
    if 'default_branch' in columns and 'branch' in columns:
        bind.execute(sa.text(
            "UPDATE repositories SET branch = default_branch WHERE branch IS NULL AND default_branch IS NOT NULL"
        ))

    # 4. Drop legacy Phase 1 columns if present
    legacy_columns = ['clone_url', 'default_branch', 'access_token', 'webhook_secret', 'is_connected']
    for col_name in legacy_columns:
        if col_name in columns:
            op.drop_column('repositories', col_name)

    # 5. Ensure disconnected_at exists
    if 'disconnected_at' not in columns:
        op.add_column('repositories', sa.Column('disconnected_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col['name'] for col in inspector.get_columns('repositories')}

    # 1. Re-add legacy repo_url (nullable to allow safe reversal)
    if 'repo_url' not in columns:
        op.add_column('repositories', sa.Column('repo_url', sa.String(length=500), nullable=True))
        if 'repository_url' in columns:
            bind.execute(sa.text(
                "UPDATE repositories SET repo_url = repository_url WHERE repository_url IS NOT NULL"
            ))

    # 2. Re-add legacy default_branch
    if 'default_branch' not in columns:
        op.add_column('repositories', sa.Column('default_branch', sa.String(length=100), server_default='main', nullable=True))
        if 'branch' in columns:
            bind.execute(sa.text(
                "UPDATE repositories SET default_branch = branch WHERE branch IS NOT NULL"
            ))

    # 3. Re-add other legacy columns
    if 'clone_url' not in columns:
        op.add_column('repositories', sa.Column('clone_url', sa.String(length=500), nullable=True))
    if 'access_token' not in columns:
        op.add_column('repositories', sa.Column('access_token', sa.String(length=500), nullable=True))
    if 'webhook_secret' not in columns:
        op.add_column('repositories', sa.Column('webhook_secret', sa.String(length=255), nullable=True))
    if 'is_connected' not in columns:
        op.add_column('repositories', sa.Column('is_connected', sa.Boolean(), server_default='false', nullable=True))
