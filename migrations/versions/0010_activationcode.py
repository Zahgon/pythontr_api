"""activationcode

Port of ``core/migrations/0010_activationcode.py``.

``code`` was a ``UUIDField``.  SQLite stored it as a 32-character hex string and
PostgreSQL as a native ``uuid``; the model now reads and writes the dashed
string form on both, so the column is a fixed-width text column.

Revision ID: 0010
Revises: 0009
"""
import sqlalchemy as sa
from alembic import op

revision = '0010'
down_revision = '0009'
branch_labels = None
depends_on = None

BIGINT = sa.BigInteger().with_variant(sa.Integer(), 'sqlite')

CONTENT_TYPES = (
    ('admin', 'logentry'),
    ('auth', 'permission'),
    ('auth', 'group'),
    ('contenttypes', 'contenttype'),
    ('sessions', 'session'),
    ('authtoken', 'token'),
    ('authtoken', 'tokenproxy'),
    ('core', 'user'),
    ('core', 'category'),
    ('core', 'article'),
    ('core', 'comment'),
    ('core', 'message'),
    ('core', 'slider'),
    ('core', 'pagevisit'),
    ('core', 'activationcode'),
)


def upgrade():
    op.create_table(
        'core_activationcode',
        sa.Column('id', BIGINT, autoincrement=True, nullable=False),
        sa.Column('code', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('is_used', sa.Boolean(), nullable=False),
        sa.Column('user_id', BIGINT, nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['core_user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'core_activationcode_user_id_73521049',
        'core_activationcode',
        ['user_id'],
    )
    # Content types used to be recorded for every installed model once the
    # whole chain had run, which is why comments store 10 for an article
    # rather than 1.  The identifiers are part of stored rows and of every
    # comment payload, so the original numbering is reproduced verbatim --
    # including the seven rows for machinery this application no longer has.
    bind = op.get_bind()
    for app_label, model in CONTENT_TYPES:
        bind.execute(
            sa.text(
                'INSERT INTO django_content_type (app_label, model) '
                'VALUES (:app_label, :model)'
            ),
            {'app_label': app_label, 'model': model},
        )


def downgrade():
    op.get_bind().execute(sa.text('DELETE FROM django_content_type'))
    op.drop_index(
        'core_activationcode_user_id_73521049',
        table_name='core_activationcode',
    )
    op.drop_table('core_activationcode')
