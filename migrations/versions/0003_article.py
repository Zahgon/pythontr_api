"""article

Port of ``core/migrations/0003_article.py``.

``core_article_categories`` is the join table Django created implicitly for the
``categories`` many-to-many.  Its surrogate key followed ``DEFAULT_AUTO_FIELD``,
so it is a big integer from the start and is not touched by revision ``0006``.

Revision ID: 0003
Revises: 0002
"""
import sqlalchemy as sa
from alembic import op

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'core_article',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('title_h1', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('read_count', sa.Integer(), nullable=False),
        sa.Column('slug', sa.String(length=150), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('is_approval', sa.Boolean(), nullable=False),
        sa.Column('is_delete', sa.Boolean(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('approval_user_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['approval_user_id'], ['core_user.id']),
        sa.ForeignKeyConstraint(['user_id'], ['core_user.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug'),
        sa.UniqueConstraint('title'),
    )
    op.create_index(
        'core_article_user_id_59ae29c7', 'core_article', ['user_id']
    )
    op.create_index(
        'core_article_approval_user_id_b1a0ab81',
        'core_article',
        ['approval_user_id'],
    )
    op.create_table(
        'core_article_categories',
        sa.Column(
            'id',
            sa.BigInteger().with_variant(sa.Integer(), 'sqlite'),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column('article_id', sa.Integer(), nullable=False),
        sa.Column('category_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['article_id'], ['core_article.id']),
        sa.ForeignKeyConstraint(['category_id'], ['core_category.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'article_id', 'category_id', name='core_article_categories_article_id_category_id_uniq'
        ),
    )
    op.create_index(
        'core_article_categories_article_id_b251527c',
        'core_article_categories',
        ['article_id'],
    )
    op.create_index(
        'core_article_categories_category_id_4d6e43c1',
        'core_article_categories',
        ['category_id'],
    )


def downgrade():
    op.drop_index(
        'core_article_categories_category_id_4d6e43c1',
        table_name='core_article_categories',
    )
    op.drop_index(
        'core_article_categories_article_id_b251527c',
        table_name='core_article_categories',
    )
    op.drop_table('core_article_categories')
    op.drop_index(
        'core_article_approval_user_id_b1a0ab81', table_name='core_article'
    )
    op.drop_index('core_article_user_id_59ae29c7', table_name='core_article')
    op.drop_table('core_article')
