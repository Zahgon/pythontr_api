"""slider

Port of ``core/migrations/0007_slider.py``.

Revision ID: 0007
Revises: 0006
"""
import sqlalchemy as sa
from alembic import op

revision = '0007'
down_revision = '0006'
branch_labels = None
depends_on = None

BIGINT = sa.BigInteger().with_variant(sa.Integer(), 'sqlite')


def upgrade():
    op.create_table(
        'core_slider',
        sa.Column('id', BIGINT, autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('link', sa.String(length=255), nullable=True),
        sa.Column('image', sa.String(length=100), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('is_approval', sa.Boolean(), nullable=False),
        sa.Column('is_delete', sa.Boolean(), nullable=False),
        sa.Column('user_id', BIGINT, nullable=True),
        sa.Column('approval_user_id', BIGINT, nullable=True),
        sa.ForeignKeyConstraint(['approval_user_id'], ['core_user.id']),
        sa.ForeignKeyConstraint(['user_id'], ['core_user.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('title'),
    )
    op.create_index('core_slider_user_id_c9b2ff03', 'core_slider', ['user_id'])
    op.create_index(
        'core_slider_approval_user_id_da732a67',
        'core_slider',
        ['approval_user_id'],
    )


def downgrade():
    op.drop_index(
        'core_slider_approval_user_id_da732a67', table_name='core_slider'
    )
    op.drop_index('core_slider_user_id_c9b2ff03', table_name='core_slider')
    op.drop_table('core_slider')
