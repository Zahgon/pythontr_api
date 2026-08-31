"""category

Port of ``core/migrations/0002_category.py``.

The Django revision opened with an ``AlterField`` that added ``blank=True`` to
``user.image``.  ``blank`` is a form-validation flag, so it produced no DDL and
has no counterpart here; the seed below is the part that matters.

The 17 ``INSERT`` statements are reproduced exactly, including the row that
spells the table ``core_Category`` -- both PostgreSQL (which folds unquoted
identifiers) and SQLite (which is case-insensitive) accept it, and rewriting it
would change the file for no reason.

Revision ID: 0002
Revises: 0001
"""
from datetime import datetime

import sqlalchemy as sa
from alembic import op

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None

ROOT_SQL = (
    'INSERT INTO core_category '
    '(name, title, title_h1, short_name, slug, created_at, updated_at) '
    'VALUES (:name, :title, :title_h1, :short_name, :slug, :created_at, :updated_at)'
)
CHILD_SQL = (
    'INSERT INTO {table} '
    '(name, title, title_h1, short_name, slug, parent_category_id, created_at, updated_at) '
    'VALUES (:name, :title, :title_h1, :short_name, :slug, :parent_category_id, '
    ':created_at, :updated_at)'
)

ROOTS = [
    ('Programlama', 'Programlama Dilleri', 'Programlama Dilleri Hakkında',
     'Programlama', 'programlama'),
    ('Veritabanı', 'Veritabanları', 'Veritabanları Hakkında',
     'Veritabanı', 'veritabani'),
    ('Sistemler / Dağıtımlar', 'Sistemler ve Dağıtımlar',
     'İşletim sistemleri ve dağıtımlar hakkında', 'Sistemler',
     'sistemler-dagitimlar'),
    ('Haberler', 'Teknoloji Haberleri', 'Teknoloji haberleri hakkında',
     'teknoloji', 'teknoloji-haberleri'),
]

# ``table`` is per row because the C# statement targets ``core_Category``.
CHILDREN = [
    ('core_category', 'Python', 'Python Programlama Dili',
     'Python Programlama Dili Hakkında', 'Python', 'python', '1'),
    ('core_category', 'Php', 'Php Programlama Dili',
     'Php Programlama Dili Hakkında', 'Php', 'php', '1'),
    ('core_category', 'Go', 'Go Programlama Dili',
     'Go Programlama Dili Hakkında', 'Go', 'go', '1'),
    ('core_Category', 'C#', 'C# Programlama Dili',
     'C# Programlama Dili Hakkında', 'C#', 'c-sharp', '1'),
    ('core_category', 'Java Script', 'Java Script Programlama Dili',
     'Java Script Programlama Frameworkleri', 'Java Script', 'javascript', '1'),
    ('core_category', 'Mobil Programlama', 'Mobil Programlama Dilleri',
     'Mobil Programlama', 'Mobil Programlama', 'mobil', '1'),
    ('core_category', 'MySql / MariaDb', 'MySql ve MariaDb veritabanları',
     'MySql ve MariaDb Veritabanları Hakkında', 'MySql / MariaDb',
     'mysql-mariadb', '2'),
    ('core_category', 'MsSql', 'MsSql Veritabanı',
     'MsSql Veritabanı Hakkında', 'MsSql', 'mssql', '2'),
    ('core_category', 'PostgreSql', 'PostgreSql Veritabanı',
     'PostgreSql Veritabanı Hakkında', 'PostgreSql', 'postgresql', '2'),
    ('core_category', 'Oracle', 'Oracle Veritabanı',
     'Oracle Veritabanı Hakkında', 'Oracle', 'oracle', '2'),
    ('core_category', 'Linux', 'Linux İşletim Sistemleri',
     'Debian \\ Ubuntu \\ Pardus vb', 'Linux', 'linux', '3'),
    ('core_category', 'OS', 'MacOs ve Ios', 'MacOs ve Ios İşletim Sistemleri',
     'macos', 'macos-ios', '3'),
    ('core_category', 'Windows X', 'Windows İşletim Sistemleri',
     'Windows İşletim Sistemi', 'Windows', 'windows', '3'),
]


def upgrade():
    op.create_table(
        'core_category',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('title_h1', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('short_name', sa.String(length=100), nullable=False),
        sa.Column('slug', sa.String(length=150), nullable=False),
        sa.Column('sort', sa.SmallInteger(), nullable=True),
        sa.Column('parent_category_id', sa.Integer(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['parent_category_id'], ['core_category.id']),
        sa.ForeignKeyConstraint(['user_id'], ['core_user.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.UniqueConstraint('short_name'),
        sa.UniqueConstraint('slug'),
        sa.UniqueConstraint('title'),
    )
    op.create_index(
        'core_category_parent_category_id_ee7dd5a5',
        'core_category',
        ['parent_category_id'],
    )
    op.create_index(
        'core_category_user_id_d4f5e86c', 'core_category', ['user_id']
    )

    bind = op.get_bind()
    for name, title, title_h1, short_name, slug in ROOTS:
        bind.execute(
            sa.text(ROOT_SQL),
            {
                'name': name,
                'title': title,
                'title_h1': title_h1,
                'short_name': short_name,
                'slug': slug,
                'created_at': datetime.now(),
                'updated_at': datetime.now(),
            },
        )
    for table, name, title, title_h1, short_name, slug, parent in CHILDREN:
        bind.execute(
            sa.text(CHILD_SQL.format(table=table)),
            {
                'name': name,
                'title': title,
                'title_h1': title_h1,
                'short_name': short_name,
                'slug': slug,
                'parent_category_id': parent,
                'created_at': datetime.now(),
                'updated_at': datetime.now(),
            },
        )


def downgrade():
    op.drop_index('core_category_user_id_d4f5e86c', table_name='core_category')
    op.drop_index(
        'core_category_parent_category_id_ee7dd5a5', table_name='core_category'
    )
    op.drop_table('core_category')
