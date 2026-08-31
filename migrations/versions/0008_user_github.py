"""user_github

Port of ``core/migrations/0008_user_github.py``.

The column is ``NOT NULL`` with no model-level default, so the empty string is
supplied as a server default for the backfill and then dropped again, which is
what Django's ``AddField`` does.

Revision ID: 0008
Revises: 0007
"""
import sqlalchemy as sa
from alembic import op

revision = '0008'
down_revision = '0007'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'core_user',
        sa.Column(
            'github', sa.String(length=255), nullable=False, server_default=''
        ),
    )
    # SQLite has no ALTER COLUMN, so the default is dropped by rebuilding the
    # table -- the same thing Django's SQLite backend does for this operation.
    with op.batch_alter_table('core_user') as batch:
        batch.alter_column('github', server_default=None)


def downgrade():
    op.drop_column('core_user', 'github')
