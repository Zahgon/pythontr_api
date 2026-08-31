"""message

Port of ``core/migrations/0005_message.py``.

Revision ID: 0005
Revises: 0004
"""
import sqlalchemy as sa
from alembic import op

revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'core_message',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('subject', sa.String(length=255), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('ip', sa.String(length=100), nullable=False),
        sa.Column('is_read', sa.Boolean(), nullable=False),
        sa.Column('is_delete', sa.Boolean(), nullable=False),
        sa.Column('is_sender_delete', sa.Boolean(), nullable=False),
        sa.Column('sender_id', sa.Integer(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['sender_id'], ['core_user.id']),
        sa.ForeignKeyConstraint(['user_id'], ['core_user.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'core_message_sender_id_0ecf4560', 'core_message', ['sender_id']
    )
    op.create_index(
        'core_message_user_id_4c5eebb2', 'core_message', ['user_id']
    )


def downgrade():
    op.drop_index('core_message_user_id_4c5eebb2', table_name='core_message')
    op.drop_index('core_message_sender_id_0ecf4560', table_name='core_message')
    op.drop_table('core_message')
