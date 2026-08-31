"""auto_20230818_2043

Port of ``core/migrations/0006_auto_20230818_2043.py``: adds ``article.image``
and promotes five primary keys from ``AutoField`` to ``BigAutoField``.

SQLite has a single 64-bit ``INTEGER`` type, so Django's backend emitted nothing
for the promotion there and neither does this revision.  On every other backend
the referencing foreign keys have to move with their targets, so they are listed
alongside them.

``django_content_type`` keeps a 32-bit key: it belongs to a contrib app that
pinned ``AutoField``, and ``core_comment.content_type_id`` points at it.

Revision ID: 0006
Revises: 0005
"""
import sqlalchemy as sa
from alembic import op

revision = '0006'
down_revision = '0005'
branch_labels = None
depends_on = None

# (table, column, nullable) in the order Django altered the models.
WIDENED = [
    ('core_article', 'id', False),
    ('core_article', 'user_id', True),
    ('core_article', 'approval_user_id', True),
    ('core_article_categories', 'article_id', False),
    ('core_article_categories', 'category_id', False),
    ('core_category', 'id', False),
    ('core_category', 'parent_category_id', True),
    ('core_category', 'user_id', True),
    ('core_comment', 'id', False),
    ('core_comment', 'user_id', True),
    ('core_message', 'id', False),
    ('core_message', 'sender_id', True),
    ('core_message', 'user_id', True),
    ('core_user', 'id', False),
    ('authtoken_token', 'user_id', False),
]


def _retype(current_type, target_type):
    if op.get_bind().dialect.name == 'sqlite':
        return
    for table, column, nullable in WIDENED:
        op.alter_column(
            table, column, existing_type=current_type, type_=target_type,
            existing_nullable=nullable,
        )


def upgrade():
    op.add_column(
        'core_article', sa.Column('image', sa.String(length=100), nullable=True)
    )
    _retype(sa.Integer(), sa.BigInteger())


def downgrade():
    _retype(sa.BigInteger(), sa.Integer())
    op.drop_column('core_article', 'image')
