"""pagevisit

Port of ``core/migrations/0009_pagevisit.py``.

The three index names are Django's generated ones and are reproduced verbatim so
an already-deployed database matches what this revision would create.

Revision ID: 0009
Revises: 0008
"""
import sqlalchemy as sa
from alembic import op

revision = '0009'
down_revision = '0008'
branch_labels = None
depends_on = None

BIGINT = sa.BigInteger().with_variant(sa.Integer(), 'sqlite')


def upgrade():
    op.create_table(
        'core_pagevisit',
        sa.Column('id', BIGINT, autoincrement=True, nullable=False),
        sa.Column('path', sa.String(length=255), nullable=False),
        sa.Column('content_id', sa.Integer(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('ip_address', sa.String(length=39), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('referrer', sa.String(length=500), nullable=True),
        sa.Column('method', sa.String(length=10), nullable=False),
        sa.Column('device_type', sa.String(length=50), nullable=False),
        sa.Column('language', sa.String(length=10), nullable=True),
        sa.Column('browser', sa.String(length=50), nullable=True),
        sa.Column('os', sa.String(length=50), nullable=True),
        sa.Column('device_brand', sa.String(length=50), nullable=True),
        sa.Column('device_model', sa.String(length=50), nullable=True),
        sa.Column('ga_client_id', sa.String(length=100), nullable=True),
        sa.Column('ga_session_id', sa.String(length=100), nullable=True),
        sa.Column('gads_id', sa.String(length=100), nullable=True),
        sa.Column('gpi_uid', sa.String(length=100), nullable=True),
        sa.Column('user_id', BIGINT, nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['core_user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'core_pagevi_timesta_df0357_idx', 'core_pagevisit', ['timestamp']
    )
    op.create_index(
        'core_pagevi_device__d70e25_idx', 'core_pagevisit', ['device_type']
    )
    op.create_index(
        'core_pagevi_ip_addr_037b80_idx', 'core_pagevisit', ['ip_address']
    )
    op.create_index(
        'core_pagevisit_user_id_af4ac1f9', 'core_pagevisit', ['user_id']
    )


def downgrade():
    op.drop_index(
        'core_pagevisit_user_id_af4ac1f9', table_name='core_pagevisit'
    )
    op.drop_index('core_pagevi_ip_addr_037b80_idx', table_name='core_pagevisit')
    op.drop_index('core_pagevi_device__d70e25_idx', table_name='core_pagevisit')
    op.drop_index('core_pagevi_timesta_df0357_idx', table_name='core_pagevisit')
    op.drop_table('core_pagevisit')
