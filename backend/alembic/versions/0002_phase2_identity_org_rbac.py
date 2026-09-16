"""Phase 2: Identity, Organization, RBAC, Sessions, and Git Metadata

Revision ID: 0002_phase2_identity_org_rbac
Revises: 0001_initial_baseline
Create Date: 2026-09-16 12:00:00.000000

"""
import uuid
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0002_phase2_identity_org_rbac'
down_revision: Union[str, None] = '0001_initial_baseline'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Canonical Baseline Role IDs for deterministic seeding
ROLE_OWNER_ID = uuid.UUID('11111111-1111-1111-1111-111111111111')
ROLE_ADMIN_ID = uuid.UUID('22222222-2222-2222-2222-222222222222')
ROLE_SECURITY_ANALYST_ID = uuid.UUID('33333333-3333-3333-3333-333333333333')
ROLE_DEVELOPER_ID = uuid.UUID('44444444-4444-4444-4444-444444444444')
ROLE_VIEWER_ID = uuid.UUID('55555555-5555-5555-5555-555555555555')


def upgrade() -> None:
    # 1. Add is_verified column to users
    op.add_column('users', sa.Column('is_verified', sa.Boolean(), server_default='false', nullable=False))

    # 2. organizations table
    op.create_table(
        'organizations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug')
    )
    op.create_index('ix_organizations_slug', 'organizations', ['slug'], unique=True)

    # 3. roles table
    op.create_table(
        'roles',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_system', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index('ix_roles_name', 'roles', ['name'], unique=True)

    # 4. permissions table
    op.create_table(
        'permissions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('key', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key')
    )
    op.create_index('ix_permissions_key', 'permissions', ['key'], unique=True)
    op.create_index('ix_permissions_category', 'permissions', ['category'])

    # 5. role_permissions table
    op.create_table(
        'role_permissions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('role_id', sa.UUID(), nullable=False),
        sa.Column('permission_id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['permission_id'], ['permissions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('role_id', 'permission_id', name='uq_role_permission')
    )
    op.create_index('ix_role_permissions_role_id', 'role_permissions', ['role_id'])
    op.create_index('ix_role_permissions_permission_id', 'role_permissions', ['permission_id'])

    # 6. organization_members table
    op.create_table(
        'organization_members',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('organization_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('role_id', sa.UUID(), nullable=False),
        sa.Column('status', sa.String(length=20), server_default='active', nullable=False),
        sa.Column('joined_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id', 'user_id', name='uq_org_member')
    )
    op.create_index('ix_org_members_org_id', 'organization_members', ['organization_id'])
    op.create_index('ix_org_members_user_id', 'organization_members', ['user_id'])
    op.create_index('ix_org_members_role_id', 'organization_members', ['role_id'])

    # 7. organization_invitations table
    op.create_table(
        'organization_invitations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('organization_id', sa.UUID(), nullable=False),
        sa.Column('invited_email', sa.String(length=320), nullable=False),
        sa.Column('role_id', sa.UUID(), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('inviter_id', sa.UUID(), nullable=True),
        sa.Column('status', sa.String(length=20), server_default='pending', nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['inviter_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token_hash')
    )
    op.create_index('ix_org_invitations_org_id', 'organization_invitations', ['organization_id'])
    op.create_index('ix_org_invitations_email', 'organization_invitations', ['invited_email'])
    op.create_index('ix_org_invitations_token_hash', 'organization_invitations', ['token_hash'], unique=True)

    # 8. sessions table
    op.create_table(
        'sessions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_used_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token_hash')
    )
    op.create_index('ix_sessions_user_id', 'sessions', ['user_id'])
    op.create_index('ix_sessions_token_hash', 'sessions', ['token_hash'], unique=True)

    # 9. verification_tokens table
    op.create_table(
        'verification_tokens',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('token_type', sa.String(length=30), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token_hash')
    )
    op.create_index('ix_verification_tokens_user_id', 'verification_tokens', ['user_id'])
    op.create_index('ix_verification_tokens_type', 'verification_tokens', ['token_type'])
    op.create_index('ix_verification_tokens_hash', 'verification_tokens', ['token_hash'], unique=True)

    # 10. api_keys table
    op.create_table(
        'api_keys',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('organization_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('key_prefix', sa.String(length=16), nullable=False),
        sa.Column('key_hash', sa.String(length=64), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key_hash')
    )
    op.create_index('ix_api_keys_org_id', 'api_keys', ['organization_id'])
    op.create_index('ix_api_keys_prefix', 'api_keys', ['key_prefix'])
    op.create_index('ix_api_keys_hash', 'api_keys', ['key_hash'], unique=True)

    # 11. repository_branches table
    op.create_table(
        'repository_branches',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('repository_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('is_default', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('head_commit_sha', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['repository_id'], ['repositories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('repository_id', 'name', name='uq_repo_branch_name')
    )
    op.create_index('ix_repo_branches_repo_id', 'repository_branches', ['repository_id'])

    # 12. repository_commits table
    op.create_table(
        'repository_commits',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('repository_id', sa.UUID(), nullable=False),
        sa.Column('commit_sha', sa.String(length=64), nullable=False),
        sa.Column('author_name', sa.String(length=255), nullable=True),
        sa.Column('author_email', sa.String(length=320), nullable=True),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('committed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['repository_id'], ['repositories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('repository_id', 'commit_sha', name='uq_repo_commit_sha')
    )
    op.create_index('ix_repo_commits_repo_id', 'repository_commits', ['repository_id'])
    op.create_index('ix_repo_commits_sha', 'repository_commits', ['commit_sha'])

    # 13. Alter projects: add organization_id
    # To handle existing projects safely, we add nullable first or create a default organization if needed
    op.add_column('projects', sa.Column('organization_id', sa.UUID(), nullable=True))
    op.create_foreign_key(
        'fk_projects_organization_id',
        'projects', 'organizations',
        ['organization_id'], ['id'],
        ondelete='RESTRICT'
    )
    op.create_index('ix_projects_organization_id', 'projects', ['organization_id'])
    op.create_unique_constraint('uq_project_org_name', 'projects', ['organization_id', 'name'])

    # 14. Alter audit_logs: add organization_id
    op.add_column('audit_logs', sa.Column('organization_id', sa.UUID(), nullable=True))
    op.create_foreign_key(
        'fk_audit_logs_organization_id',
        'audit_logs', 'organizations',
        ['organization_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_index('ix_audit_logs_org_id', 'audit_logs', ['organization_id'])

    # ── SEED ROLES & PERMISSIONS ──────────────────────────────────────
    now = datetime.now(timezone.utc)

    roles_table = sa.table(
        'roles',
        sa.column('id', sa.UUID()),
        sa.column('name', sa.String()),
        sa.column('description', sa.Text()),
        sa.column('is_system', sa.Boolean()),
        sa.column('created_at', sa.DateTime(timezone=True)),
        sa.column('updated_at', sa.DateTime(timezone=True)),
    )

    op.bulk_insert(
        roles_table,
        [
            {'id': ROLE_OWNER_ID, 'name': 'owner', 'description': 'Full administrative control over organization and all resources', 'is_system': True, 'created_at': now, 'updated_at': now},
            {'id': ROLE_ADMIN_ID, 'name': 'admin', 'description': 'Organization administration and team management', 'is_system': True, 'created_at': now, 'updated_at': now},
            {'id': ROLE_SECURITY_ANALYST_ID, 'name': 'security_analyst', 'description': 'Scan and finding triage, vulnerability remediation management', 'is_system': True, 'created_at': now, 'updated_at': now},
            {'id': ROLE_DEVELOPER_ID, 'name': 'developer', 'description': 'Access to assigned projects, scans, and remediation requests', 'is_system': True, 'created_at': now, 'updated_at': now},
            {'id': ROLE_VIEWER_ID, 'name': 'viewer', 'description': 'Read-only access across authorized projects, scans, and findings', 'is_system': True, 'created_at': now, 'updated_at': now},
        ]
    )

    permissions_table = sa.table(
        'permissions',
        sa.column('id', sa.UUID()),
        sa.column('key', sa.String()),
        sa.column('description', sa.Text()),
        sa.column('category', sa.String()),
        sa.column('created_at', sa.DateTime(timezone=True)),
        sa.column('updated_at', sa.DateTime(timezone=True)),
    )

    # Canonical Baseline Permission Vocabulary
    PERMS = [
        # Organization
        ('organization.read', 'View organization details', 'organization'),
        ('organization.update', 'Update organization settings', 'organization'),
        ('organization.delete', 'Delete organization (owner only)', 'organization'),
        # Team
        ('team.read', 'View team members', 'team'),
        ('team.invite', 'Invite new team members', 'team'),
        ('team.remove', 'Remove team members', 'team'),
        ('team.role.update', 'Change member roles', 'team'),
        # Projects
        ('project.read', 'View projects', 'project'),
        ('project.create', 'Create new projects', 'project'),
        ('project.update', 'Update project details', 'project'),
        ('project.delete', 'Delete/archive projects', 'project'),
        # Repositories
        ('repository.read', 'View repositories and Git metadata', 'repository'),
        ('repository.create', 'Link repository to project', 'repository'),
        ('repository.update', 'Update repository settings', 'repository'),
        ('repository.delete', 'Unlink repository', 'repository'),
        # Scans
        ('scan.read', 'View scans and scan history', 'scan'),
        ('scan.create', 'Dispatch new scan execution', 'scan'),
        ('scan.cancel', 'Cancel queued or running scan', 'scan'),
        # Findings
        ('finding.read', 'View vulnerability findings and call graphs', 'finding'),
        ('finding.update', 'Update finding status or severity', 'finding'),
        ('finding.assign', 'Assign finding to developer', 'finding'),
        ('finding.suppress', 'Suppress false positive finding', 'finding'),
        ('finding.accept_risk', 'Mark finding as accepted risk', 'finding'),
        # Remediation
        ('remediation.read', 'View remediation proposals', 'remediation'),
        ('remediation.create', 'Request automated remediation patch', 'remediation'),
        ('remediation.apply', 'Apply remediation patch', 'remediation'),
        ('remediation.approve', 'Approve remediation patch', 'remediation'),
        # Reports
        ('report.read', 'View security audit reports', 'report'),
        ('report.create', 'Generate security audit reports', 'report'),
        # Integrations
        ('integration.manage', 'Configure external integrations (GitHub, Jira)', 'integration'),
        # Settings
        ('settings.read', 'View workspace settings', 'settings'),
        ('settings.manage', 'Manage workspace configuration', 'settings'),
        # Audit
        ('audit.read', 'Inspect security audit logs', 'audit'),
        # API Keys
        ('api_key.read', 'View API key metadata', 'api_key'),
        ('api_key.create', 'Generate new API keys', 'api_key'),
        ('api_key.revoke', 'Revoke active API keys', 'api_key'),
    ]

    perm_records = []
    perm_id_map = {}
    for key, desc, cat in PERMS:
        pid = uuid.uuid4()
        perm_id_map[key] = pid
        perm_records.append({
            'id': pid,
            'key': key,
            'description': desc,
            'category': cat,
            'created_at': now,
            'updated_at': now
        })

    op.bulk_insert(permissions_table, perm_records)

    # ── ROLE-PERMISSION MAPPINGS ──────────────────────────────────────
    role_permissions_table = sa.table(
        'role_permissions',
        sa.column('id', sa.UUID()),
        sa.column('role_id', sa.UUID()),
        sa.column('permission_id', sa.UUID()),
        sa.column('created_at', sa.DateTime(timezone=True)),
    )

    all_keys = [k for k, _, _ in PERMS]

    owner_keys = set(all_keys)
    admin_keys = set(all_keys) - {'organization.delete'}
    analyst_keys = {
        'organization.read', 'team.read',
        'project.read', 'repository.read',
        'scan.read', 'scan.create', 'scan.cancel',
        'finding.read', 'finding.update', 'finding.assign', 'finding.suppress', 'finding.accept_risk',
        'remediation.read', 'remediation.create',
        'report.read', 'report.create',
        'settings.read', 'audit.read',
    }
    developer_keys = {
        'organization.read', 'team.read',
        'project.read', 'repository.read',
        'scan.read', 'scan.create',
        'finding.read',
        'remediation.read', 'remediation.create', 'remediation.apply',
        'report.read',
        'settings.read',
    }
    viewer_keys = {
        'organization.read', 'team.read',
        'project.read', 'repository.read',
        'scan.read', 'finding.read',
        'remediation.read', 'report.read',
        'settings.read',
    }

    role_matrix = [
        (ROLE_OWNER_ID, owner_keys),
        (ROLE_ADMIN_ID, admin_keys),
        (ROLE_SECURITY_ANALYST_ID, analyst_keys),
        (ROLE_DEVELOPER_ID, developer_keys),
        (ROLE_VIEWER_ID, viewer_keys),
    ]

    rp_records = []
    for role_id, keys in role_matrix:
        for k in keys:
            rp_records.append({
                'id': uuid.uuid4(),
                'role_id': role_id,
                'permission_id': perm_id_map[k],
                'created_at': now,
            })

    op.bulk_insert(role_permissions_table, rp_records)


def downgrade() -> None:
    # Remove foreign keys and columns added to Phase 1 tables
    op.drop_index('ix_audit_logs_org_id', table_name='audit_logs')
    op.drop_constraint('fk_audit_logs_organization_id', 'audit_logs', type_='foreignkey')
    op.drop_column('audit_logs', 'organization_id')

    op.drop_constraint('uq_project_org_name', 'projects', type_='unique')
    op.drop_index('ix_projects_organization_id', table_name='projects')
    op.drop_constraint('fk_projects_organization_id', 'projects', type_='foreignkey')
    op.drop_column('projects', 'organization_id')

    # Drop repository_commits and repository_branches
    op.drop_index('ix_repo_commits_sha', table_name='repository_commits')
    op.drop_index('ix_repo_commits_repo_id', table_name='repository_commits')
    op.drop_table('repository_commits')
    op.drop_index('ix_repo_branches_repo_id', table_name='repository_branches')
    op.drop_table('repository_branches')

    # Drop api_keys
    op.drop_index('ix_api_keys_hash', table_name='api_keys')
    op.drop_index('ix_api_keys_prefix', table_name='api_keys')
    op.drop_index('ix_api_keys_org_id', table_name='api_keys')
    op.drop_table('api_keys')

    # Drop verification_tokens
    op.drop_index('ix_verification_tokens_hash', table_name='verification_tokens')
    op.drop_index('ix_verification_tokens_type', table_name='verification_tokens')
    op.drop_index('ix_verification_tokens_user_id', table_name='verification_tokens')
    op.drop_table('verification_tokens')

    # Drop sessions
    op.drop_index('ix_sessions_token_hash', table_name='sessions')
    op.drop_index('ix_sessions_user_id', table_name='sessions')
    op.drop_table('sessions')

    # Drop organization_invitations
    op.drop_index('ix_org_invitations_token_hash', table_name='organization_invitations')
    op.drop_index('ix_org_invitations_email', table_name='organization_invitations')
    op.drop_index('ix_org_invitations_org_id', table_name='organization_invitations')
    op.drop_table('organization_invitations')

    # Drop organization_members
    op.drop_index('ix_org_members_role_id', table_name='organization_members')
    op.drop_index('ix_org_members_user_id', table_name='organization_members')
    op.drop_index('ix_org_members_org_id', table_name='organization_members')
    op.drop_table('organization_members')

    # Drop organizations
    op.drop_index('ix_organizations_slug', table_name='organizations')
    op.drop_table('organizations')

    # Drop role_permissions, permissions, roles
    op.drop_table('role_permissions')
    op.drop_index('ix_permissions_category', table_name='permissions')
    op.drop_index('ix_permissions_key', table_name='permissions')
    op.drop_table('permissions')
    op.drop_index('ix_roles_name', table_name='roles')
    op.drop_table('roles')

    # Remove is_verified from users
    op.drop_column('users', 'is_verified')
