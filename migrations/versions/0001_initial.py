"""initial

Port of ``core/migrations/0001_initial.py``.

The Django revision only created ``core_user``; ``django_content_type`` and
``authtoken_token`` arrived with the ``contenttypes`` and ``rest_framework.
authtoken`` apps, whose own migrations no longer exist.  Both tables are still
read by this project, so they are created here instead of vanishing with the
apps that used to own them.

``core_user`` loses the ``groups`` / ``user_permissions`` join tables: they came
from ``PermissionsMixin``, and nothing in the project ever queried them.

Revision ID: 0001
Revises:
"""
import sqlalchemy as sa
from alembic import op

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'django_content_type',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('app_label', sa.String(length=100), nullable=False),
        sa.Column('model', sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'app_label', 'model', name='django_content_type_app_label_model_uniq'
        ),
    )
    op.create_table(
        'core_user',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('password', sa.String(length=128), nullable=False),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.Column('is_superuser', sa.Boolean(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('username', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('surname', sa.String(length=255), nullable=False),
        sa.Column('image', sa.String(length=100), nullable=True),
        sa.Column('about_me', sa.Text(), nullable=False),
        sa.Column('linkedin', sa.String(length=255), nullable=False),
        sa.Column('is_notification_email', sa.Boolean(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('is_staff', sa.Boolean(), nullable=False),
        sa.Column('is_ban', sa.Boolean(), nullable=False),
        sa.Column('is_delete', sa.Boolean(), nullable=False),
        sa.Column('slug', sa.String(length=150), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('slug'),
        sa.UniqueConstraint('username'),
    )
    op.create_table(
        'authtoken_token',
        sa.Column('key', sa.String(length=40), nullable=False),
        sa.Column('created', sa.DateTime(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['core_user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('key'),
        sa.UniqueConstraint('user_id'),
    )


def downgrade():
    op.drop_table('authtoken_token')
    op.drop_table('core_user')
    op.drop_table('django_content_type')
