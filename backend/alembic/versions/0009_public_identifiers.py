"""Add public identifiers to projects, scans, source_snapshots, and reports

Revision ID: 0009_public_identifiers
Revises: 0008_phase6_xai_remediation
Create Date: 2026-09-17 15:40:00.000000

"""
from typing import Sequence, Union
import secrets

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0009_public_identifiers'
down_revision: Union[str, None] = '0008_phase6_xai_remediation'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyz"

TABLE_CONFIGS = [
    ("projects", "prj"),
    ("scans", "scn"),
    ("source_snapshots", "snp"),
    ("reports", "rpt"),
]


def _generate_id(prefix: str) -> str:
    return f"{prefix}_{''.join(secrets.choice(ALPHABET) for _ in range(12))}"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    for table_name, prefix in TABLE_CONFIGS:
        if table_name not in existing_tables:
            continue

        existing_columns = {col['name'] for col in inspector.get_columns(table_name)}
        if 'public_id' not in existing_columns:
            op.add_column(table_name, sa.Column('public_id', sa.String(32), nullable=True))

            # Backfill any existing rows
            t_meta = sa.Table(
                table_name,
                sa.MetaData(),
                sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
                sa.Column('public_id', sa.String(32)),
            )
            rows = bind.execute(sa.select(t_meta.c.id).where(t_meta.c.public_id.is_(None))).fetchall()
            assigned = set()
            for (row_id,) in rows:
                new_pid = _generate_id(prefix)
                while new_pid in assigned:
                    new_pid = _generate_id(prefix)
                assigned.add(new_pid)
                bind.execute(
                    sa.update(t_meta).where(t_meta.c.id == row_id).values(public_id=new_pid)
                )

            # Set nullable=False and unique index
            op.alter_column(table_name, 'public_id', nullable=False)
            existing_indexes = {ix['name'] for ix in inspector.get_indexes(table_name)}
            ix_name = f"ix_{table_name}_public_id"
            if ix_name not in existing_indexes:
                op.create_index(ix_name, table_name, ['public_id'], unique=True)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    for table_name, _ in reversed(TABLE_CONFIGS):
        if table_name not in existing_tables:
            continue
        existing_indexes = {ix['name'] for ix in inspector.get_indexes(table_name)}
        ix_name = f"ix_{table_name}_public_id"
        if ix_name in existing_indexes:
            op.drop_index(ix_name, table_name=table_name)

        existing_columns = {col['name'] for col in inspector.get_columns(table_name)}
        if 'public_id' in existing_columns:
            op.drop_column(table_name, 'public_id')
