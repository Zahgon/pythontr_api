"""comment

Port of ``core/migrations/0004_comment.py``.

``object_id`` was a ``PositiveIntegerField``, which Django backs with a plain
integer column plus a non-negative check, so the check is written out here.

Revision ID: 0004
Revises: 0003
"""
import sqlalchemy as sa
from alembic import op

revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'core_comment',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('content_type_id', sa.Integer(), nullable=False),
        sa.Column('object_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('email', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('ip', sa.String(length=100), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('is_delete', sa.Boolean(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.CheckConstraint(
            'object_id >= 0', name='core_comment_object_id_positive_check'
        ),
        sa.ForeignKeyConstraint(
            ['content_type_id'], ['django_content_type.id'], ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(['user_id'], ['core_user.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'core_comment_content_type_id_7affec6d',
        'core_comment',
        ['content_type_id'],
    )
    op.create_index(
        'core_comment_user_id_a9a9430c', 'core_comment', ['user_id']
    )


def downgrade():
    op.drop_index('core_comment_user_id_a9a9430c', table_name='core_comment')
    op.drop_index(
        'core_comment_content_type_id_7affec6d', table_name='core_comment'
    )
    op.drop_table('core_comment')
