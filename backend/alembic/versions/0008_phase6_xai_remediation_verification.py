"""Phase 6: XAI explanations, model registry, remediations, isolated validations, and verification

Revision ID: 0008_phase6_xai_remediation_verification
Revises: 0007_phase5_ai_and_findings
Create Date: 2026-09-17 14:00:00.000000

"""
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0008_phase6_xai_remediation'
down_revision: Union[str, None] = '0007_phase5_ai_and_findings'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    # 1. model_versions table
    if 'model_versions' not in existing_tables:
        op.create_table(
            'model_versions',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
            sa.Column('model_name', sa.String(length=100), nullable=False),
            sa.Column('version', sa.String(length=50), nullable=False),
            sa.Column('provider', sa.String(length=100), nullable=False),
            sa.Column('artifact_uri', sa.String(length=1024), nullable=True),
            sa.Column('checksum', sa.String(length=64), nullable=True),
            sa.Column('runtime', sa.String(length=50), nullable=False, server_default='mock'),
            sa.Column('input_schema_version', sa.String(length=50), nullable=False, server_default='v1.0.0'),
            sa.Column('output_schema_version', sa.String(length=50), nullable=False, server_default='v1.0.0'),
            sa.Column('status', sa.String(length=50), nullable=False, server_default='inactive'),
            sa.Column('metadata_json', postgresql.JSON(), nullable=True),
            sa.Column('activated_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index('ix_model_versions_model_name', 'model_versions', ['model_name'])
        op.create_index('ix_model_versions_version', 'model_versions', ['version'])
        op.create_index('ix_model_versions_provider', 'model_versions', ['provider'])
        op.create_index('ix_model_versions_status', 'model_versions', ['status'])

    # 2. ai_explanations table
    if 'ai_explanations' not in existing_tables:
        op.create_table(
            'ai_explanations',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
            sa.Column('finding_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('prediction_id', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('source_snapshot_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('provider', sa.String(length=100), nullable=False),
            sa.Column('model_name', sa.String(length=100), nullable=False),
            sa.Column('model_version', sa.String(length=50), nullable=False),
            sa.Column('explanation_method', sa.String(length=50), nullable=False, server_default='evidence_synthesizer'),
            sa.Column('schema_version', sa.String(length=50), nullable=False, server_default='v1.0.0'),
            sa.Column('summary', sa.Text(), nullable=False),
            sa.Column('root_cause', sa.Text(), nullable=False),
            sa.Column('why_vulnerable', sa.Text(), nullable=False),
            sa.Column('impact', sa.Text(), nullable=False),
            sa.Column('evidence_explanation', sa.Text(), nullable=False),
            sa.Column('warnings', postgresql.JSON(), nullable=False, server_default='[]'),
            sa.Column('confidence', sa.Float(), nullable=True),
            sa.Column('generated_by_ai', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('artifact_uri', sa.String(length=1024), nullable=True),
            sa.Column('checksum', sa.String(length=64), nullable=True),
            sa.Column('important_locations', postgresql.JSON(), nullable=False, server_default='[]'),
            sa.Column('important_tokens', postgresql.JSON(), nullable=False, server_default='[]'),
            sa.Column('important_functions', postgresql.JSON(), nullable=False, server_default='[]'),
            sa.Column('important_nodes', postgresql.JSON(), nullable=False, server_default='[]'),
            sa.Column('important_edges', postgresql.JSON(), nullable=False, server_default='[]'),
            sa.Column('method_status', sa.String(length=50), nullable=False, server_default='COMPLETED'),
            sa.Column('status_reason', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(['finding_id'], ['findings.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['prediction_id'], ['ai_predictions.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['source_snapshot_id'], ['source_snapshots.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        )
        op.create_index('ix_ai_explanations_finding_id', 'ai_explanations', ['finding_id'])
        op.create_index('ix_ai_explanations_prediction_id', 'ai_explanations', ['prediction_id'])
        op.create_index('ix_ai_explanations_source_snapshot_id', 'ai_explanations', ['source_snapshot_id'])
        op.create_index('ix_ai_explanations_organization_id', 'ai_explanations', ['organization_id'])
        op.create_index('ix_ai_explanations_project_id', 'ai_explanations', ['project_id'])
        op.create_index('ix_ai_explanations_explanation_method', 'ai_explanations', ['explanation_method'])
        op.create_index('ix_ai_explanations_method_status', 'ai_explanations', ['method_status'])

    # 3. remediations table
    if 'remediations' not in existing_tables:
        op.create_table(
            'remediations',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
            sa.Column('finding_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('source_snapshot_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('remediation_number', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('provider', sa.String(length=100), nullable=False),
            sa.Column('model_name', sa.String(length=100), nullable=False),
            sa.Column('model_version', sa.String(length=50), nullable=False),
            sa.Column('prompt_version', sa.String(length=50), nullable=False, server_default='v1.0.0'),
            sa.Column('status', sa.String(length=50), nullable=False, server_default='GENERATED'),
            sa.Column('summary', sa.Text(), nullable=False),
            sa.Column('explanation', sa.Text(), nullable=False),
            sa.Column('diff_content', sa.Text(), nullable=False),
            sa.Column('patch_artifact_uri', sa.String(length=1024), nullable=True),
            sa.Column('patch_checksum', sa.String(length=64), nullable=False),
            sa.Column('changed_files', postgresql.JSON(), nullable=False, server_default='[]'),
            sa.Column('confidence', sa.Float(), nullable=True),
            sa.Column('warnings', postgresql.JSON(), nullable=False, server_default='[]'),
            sa.Column('generated_by_ai', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('is_active_candidate', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('created_by_user_id', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('reviewed_by_user_id', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('review_comment', sa.Text(), nullable=True),
            sa.Column('superseded_by_id', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(['finding_id'], ['findings.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['source_snapshot_id'], ['source_snapshots.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['reviewed_by_user_id'], ['users.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['superseded_by_id'], ['remediations.id'], ondelete='SET NULL'),
        )
        op.create_index('ix_remediations_finding_id', 'remediations', ['finding_id'])
        op.create_index('ix_remediations_organization_id', 'remediations', ['organization_id'])
        op.create_index('ix_remediations_project_id', 'remediations', ['project_id'])
        op.create_index('ix_remediations_status', 'remediations', ['status'])
        op.create_index('ix_remediations_is_active_candidate', 'remediations', ['is_active_candidate'])

    # 4. remediation_validations table
    if 'remediation_validations' not in existing_tables:
        op.create_table(
            'remediation_validations',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
            sa.Column('remediation_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('finding_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('source_snapshot_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('attempt_number', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('workspace_identifier', sa.String(length=255), nullable=False),
            sa.Column('validation_policy_version', sa.String(length=50), nullable=False, server_default='v1.0.0'),
            sa.Column('status', sa.String(length=50), nullable=False, server_default='PREPARING'),
            sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('timeout_seconds', sa.Integer(), nullable=False, server_default='300'),
            sa.Column('patch_apply_result', postgresql.JSON(), nullable=False, server_default='{}'),
            sa.Column('syntax_result', postgresql.JSON(), nullable=False, server_default='{}'),
            sa.Column('build_result', postgresql.JSON(), nullable=False, server_default='{}'),
            sa.Column('test_result', postgresql.JSON(), nullable=False, server_default='{}'),
            sa.Column('static_analysis_result', postgresql.JSON(), nullable=False, server_default='{}'),
            sa.Column('taint_result', postgresql.JSON(), nullable=False, server_default='{}'),
            sa.Column('graph_result', postgresql.JSON(), nullable=False, server_default='{}'),
            sa.Column('regression_result', postgresql.JSON(), nullable=False, server_default='{}'),
            sa.Column('verification_scan_id', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('final_verification_result', sa.String(length=50), nullable=False, server_default='PENDING'),
            sa.Column('failure_reason', sa.Text(), nullable=True),
            sa.Column('logs_artifact_uri', sa.String(length=1024), nullable=True),
            sa.Column('artifact_checksum', sa.String(length=64), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(['remediation_id'], ['remediations.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['finding_id'], ['findings.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['source_snapshot_id'], ['source_snapshots.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['verification_scan_id'], ['scans.id'], ondelete='SET NULL'),
        )
        op.create_index('ix_remediation_validations_remediation_id', 'remediation_validations', ['remediation_id'])
        op.create_index('ix_remediation_validations_finding_id', 'remediation_validations', ['finding_id'])
        op.create_index('ix_remediation_validations_organization_id', 'remediation_validations', ['organization_id'])
        op.create_index('ix_remediation_validations_project_id', 'remediation_validations', ['project_id'])
        op.create_index('ix_remediation_validations_status', 'remediation_validations', ['status'])
        op.create_index('ix_remediation_validations_final_verification_result', 'remediation_validations', ['final_verification_result'])

    # 5. Seed Phase 6 RBAC permissions
    permissions_table = sa.table(
        'permissions',
        sa.column('id', postgresql.UUID(as_uuid=True)),
        sa.column('key', sa.String),
        sa.column('description', sa.Text),
        sa.column('category', sa.String),
        sa.column('created_at', sa.DateTime(timezone=True)),
        sa.column('updated_at', sa.DateTime(timezone=True)),
    )
    roles_table = sa.table(
        'roles',
        sa.column('id', postgresql.UUID(as_uuid=True)),
        sa.column('name', sa.String),
    )
    role_permissions_table = sa.table(
        'role_permissions',
        sa.column('id', postgresql.UUID(as_uuid=True)),
        sa.column('role_id', postgresql.UUID(as_uuid=True)),
        sa.column('permission_id', postgresql.UUID(as_uuid=True)),
        sa.column('created_at', sa.DateTime(timezone=True)),
    )

    new_permissions = [
        ('explanation.read', 'View vulnerability explanation and XAI attributions', 'explanation'),
        ('explanation.generate', 'Generate evidence-aware explanation and XAI attributions', 'explanation'),
        ('remediation.read', 'View remediation proposals and unified diffs', 'remediation'),
        ('remediation.generate', 'Generate proposed remediation and secure fix diff', 'remediation'),
        ('remediation.review', 'Approve or reject proposed remediations', 'remediation'),
        ('remediation.apply', 'Apply remediation to isolated validation workspace', 'remediation'),
        ('remediation.validate', 'Execute multi-stage validation and verification scans', 'remediation'),
        ('finding.mark_fixed', 'Mark finding as fixed following validated remediation', 'finding'),
        ('finding.verify', 'Verify finding resolution following verification scan', 'finding'),
    ]

    for key, desc, cat in new_permissions:
        check = bind.execute(sa.text("SELECT id FROM permissions WHERE key = :k"), {"k": key}).fetchone()
        if not check:
            p_id = uuid.uuid4()
            bind.execute(
                permissions_table.insert().values(
                    id=p_id,
                    key=key,
                    description=desc,
                    category=cat,
                    created_at=sa.func.now(),
                    updated_at=sa.func.now(),
                )
            )

    # Grant new permissions to privileged roles (owner, admin, security_analyst)
    privileged_roles = ['owner', 'admin', 'security_analyst']
    all_new_keys = [k for k, _, _ in new_permissions]
    for r_name in privileged_roles:
        role_row = bind.execute(sa.text("SELECT id FROM roles WHERE name = :n"), {"n": r_name}).fetchone()
        if role_row:
            role_id = role_row[0]
            for p_key in all_new_keys:
                perm_row = bind.execute(sa.text("SELECT id FROM permissions WHERE key = :k"), {"k": p_key}).fetchone()
                if perm_row:
                    perm_id = perm_row[0]
                    link_check = bind.execute(
                        sa.text("SELECT id FROM role_permissions WHERE role_id = :r AND permission_id = :p"),
                        {"r": role_id, "p": perm_id},
                    ).fetchone()
                    if not link_check:
                        bind.execute(
                            role_permissions_table.insert().values(
                                id=uuid.uuid4(),
                                role_id=role_id,
                                permission_id=perm_id,
                                created_at=sa.func.now(),
                            )
                        )

    # Grant read permissions to developer and viewer
    read_keys = ['explanation.read', 'remediation.read']
    for r_name in ['developer', 'viewer']:
        role_row = bind.execute(sa.text("SELECT id FROM roles WHERE name = :n"), {"n": r_name}).fetchone()
        if role_row:
            role_id = role_row[0]
            for p_key in read_keys:
                perm_row = bind.execute(sa.text("SELECT id FROM permissions WHERE key = :k"), {"k": p_key}).fetchone()
                if perm_row:
                    perm_id = perm_row[0]
                    link_check = bind.execute(
                        sa.text("SELECT id FROM role_permissions WHERE role_id = :r AND permission_id = :p"),
                        {"r": role_id, "p": perm_id},
                    ).fetchone()
                    if not link_check:
                        bind.execute(
                            role_permissions_table.insert().values(
                                id=uuid.uuid4(),
                                role_id=role_id,
                                permission_id=perm_id,
                                created_at=sa.func.now(),
                            )
                        )


def downgrade() -> None:
    op.drop_table('remediation_validations')
    op.drop_table('remediations')
    op.drop_table('ai_explanations')
    op.drop_table('model_versions')
