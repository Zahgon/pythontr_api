"""initial schema

One consolidated revision. It creates the tables the old migration history had grown to by
its last revision, and it writes the two row sets that are SCHEMA rather than fixtures: the
frozen content-type numbering a comment's ``content_type_id`` already points at, and the
seventeen default categories. Those categories were inserted by raw SQL, so they bypassed
the column default on ``sort`` and carry NULL there; that is reproduced.

Revision ID: 0001_initial
Revises:
"""
from datetime import datetime

import sqlalchemy as sa
from alembic import op

revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None

# A fixed stamp, so the schema a fresh database gets is the same on every run.
SEEDED_AT = datetime(2020, 1, 17, 20, 0, 0)

CONTENT_TYPES = [
    (1, 'admin', 'logentry'), (2, 'auth', 'permission'), (3, 'auth', 'group'),
    (4, 'contenttypes', 'contenttype'), (5, 'sessions', 'session'),
    (6, 'authtoken', 'token'), (7, 'authtoken', 'tokenproxy'),
    (8, 'core', 'user'), (9, 'core', 'category'), (10, 'core', 'article'),
    (11, 'core', 'comment'), (12, 'core', 'message'), (13, 'core', 'slider'),
    (14, 'core', 'pagevisit'), (15, 'core', 'activationcode'),
]

ROOTS = [
    ('Programlama', 'Programlama Dilleri', 'Programlama Dilleri Hakkında',
     'Programlama', 'programlama'),
    ('Veritabanı', 'Veritabanları', 'Veritabanları Hakkında', 'Veritabanı',
     'veritabani'),
    ('Sistemler / Dağıtımlar', 'Sistemler ve Dağıtımlar',
     'İşletim sistemleri ve dağıtımlar hakkında', 'Sistemler',
     'sistemler-dagitimlar'),
    ('Haberler', 'Teknoloji Haberleri', 'Teknoloji haberleri hakkında', 'teknoloji',
     'teknoloji-haberleri'),
]

CHILDREN = [
    ('Python', 'Python Programlama Dili', 'Python Programlama Dili Hakkında', 'Python',
     'python', 1),
    ('Php', 'Php Programlama Dili', 'Php Programlama Dili Hakkında', 'Php', 'php', 1),
    ('Go', 'Go Programlama Dili', 'Go Programlama Dili Hakkında', 'Go', 'go', 1),
    ('C#', 'C# Programlama Dili', 'C# Programlama Dili Hakkında', 'C#', 'c-sharp', 1),
    ('Java Script', 'Java Script Programlama Dili',
     'Java Script Programlama Frameworkleri', 'Java Script', 'javascript', 1),
    ('Mobil Programlama', 'Mobil Programlama Dilleri', 'Mobil Programlama',
     'Mobil Programlama', 'mobil', 1),
    ('MySql / MariaDb', 'MySql ve MariaDb veritabanları',
     'MySql ve MariaDb Veritabanları Hakkında', 'MySql / MariaDb', 'mysql-mariadb', 2),
    ('MsSql', 'MsSql Veritabanı', 'MsSql Veritabanı Hakkında', 'MsSql', 'mssql', 2),
    ('PostgreSql', 'PostgreSql Veritabanı', 'PostgreSql Veritabanı Hakkında',
     'PostgreSql', 'postgresql', 2),
    ('Oracle', 'Oracle Veritabanı', 'Oracle Veritabanı Hakkında', 'Oracle', 'oracle', 2),
    ('Linux', 'Linux İşletim Sistemleri', 'Debian \\ Ubuntu \\ Pardus vb', 'Linux',
     'linux', 3),
    ('OS', 'MacOs ve Ios', 'MacOs ve Ios İşletim Sistemleri', 'macos', 'macos-ios', 3),
    ('Windows X', 'Windows İşletim Sistemleri', 'Windows İşletim Sistemi', 'Windows',
     'windows', 3),
]


def upgrade():
    op.create_table(
        'django_content_type',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('app_label', sa.String(100), nullable=False),
        sa.Column('model', sa.String(100), nullable=False),
    )
    op.create_table(
        'core_user',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('password', sa.String(128), nullable=False),
        sa.Column('last_login', sa.DateTime, nullable=True),
        sa.Column('is_superuser', sa.Boolean, nullable=False),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('username', sa.String(255), nullable=False, unique=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('surname', sa.String(255), nullable=False),
        sa.Column('image', sa.String(100), nullable=True),
        sa.Column('about_me', sa.Text, nullable=False),
        sa.Column('linkedin', sa.String(255), nullable=False),
        sa.Column('github', sa.String(255), nullable=False),
        sa.Column('is_notification_email', sa.Boolean, nullable=False),
        sa.Column('is_active', sa.Boolean, nullable=False),
        sa.Column('is_staff', sa.Boolean, nullable=False),
        sa.Column('is_ban', sa.Boolean, nullable=False),
        sa.Column('is_delete', sa.Boolean, nullable=False),
        sa.Column('slug', sa.String(150), nullable=False, unique=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
    )
    op.create_table(
        'authtoken_token',
        sa.Column('key', sa.String(40), primary_key=True),
        sa.Column('created', sa.DateTime, nullable=False),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('core_user.id'), nullable=False,
                  unique=True),
    )
    op.create_table(
        'core_category',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
        sa.Column('name', sa.String(255), nullable=False, unique=True),
        sa.Column('title', sa.String(255), nullable=False, unique=True),
        sa.Column('title_h1', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('content', sa.Text, nullable=True),
        sa.Column('short_name', sa.String(100), nullable=False, unique=True),
        sa.Column('slug', sa.String(150), nullable=False, unique=True),
        sa.Column('sort', sa.SmallInteger, nullable=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('core_user.id'), nullable=True),
        sa.Column('parent_category_id', sa.Integer, sa.ForeignKey('core_category.id'),
                  nullable=True),
    )
    op.create_table(
        'core_article',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
        sa.Column('title', sa.String(255), nullable=False, unique=True),
        sa.Column('title_h1', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('image', sa.String(100), nullable=True),
        sa.Column('read_count', sa.Integer, nullable=False),
        sa.Column('slug', sa.String(150), nullable=False, unique=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('core_user.id'), nullable=True),
        sa.Column('is_active', sa.Boolean, nullable=False),
        sa.Column('is_approval', sa.Boolean, nullable=False),
        sa.Column('approval_user_id', sa.Integer, sa.ForeignKey('core_user.id'),
                  nullable=True),
        sa.Column('is_delete', sa.Boolean, nullable=False),
    )
    op.create_table(
        'core_article_categories',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('article_id', sa.Integer, sa.ForeignKey('core_article.id'),
                  nullable=False),
        sa.Column('category_id', sa.Integer, sa.ForeignKey('core_category.id'),
                  nullable=False),
    )
    op.create_table(
        'core_comment',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('object_id', sa.Integer, nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('email', sa.String(100), nullable=False),
        sa.Column('name', sa.String(50), nullable=False),
        sa.Column('ip', sa.String(100), nullable=False),
        sa.Column('is_active', sa.Boolean, nullable=False),
        sa.Column('is_delete', sa.Boolean, nullable=False),
        sa.Column('content_type_id', sa.Integer,
                  sa.ForeignKey('django_content_type.id'), nullable=False),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('core_user.id'), nullable=True),
    )
    op.create_table(
        'core_message',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('subject', sa.String(255), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('ip', sa.String(100), nullable=False),
        sa.Column('is_read', sa.Boolean, nullable=False),
        sa.Column('is_delete', sa.Boolean, nullable=False),
        sa.Column('is_sender_delete', sa.Boolean, nullable=False),
        sa.Column('sender_id', sa.Integer, sa.ForeignKey('core_user.id'), nullable=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('core_user.id'), nullable=True),
    )
    op.create_table(
        'core_slider',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
        sa.Column('title', sa.String(255), nullable=False, unique=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('link', sa.String(255), nullable=True),
        sa.Column('image', sa.String(100), nullable=True),
        sa.Column('is_active', sa.Boolean, nullable=False),
        sa.Column('is_approval', sa.Boolean, nullable=False),
        sa.Column('is_delete', sa.Boolean, nullable=False),
        sa.Column('approval_user_id', sa.Integer, sa.ForeignKey('core_user.id'),
                  nullable=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('core_user.id'), nullable=True),
    )
    op.create_table(
        'core_pagevisit',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('path', sa.String(255), nullable=False),
        sa.Column('content_id', sa.Integer, nullable=True),
        sa.Column('timestamp', sa.DateTime, nullable=False),
        sa.Column('ip_address', sa.String(39), nullable=True),
        sa.Column('user_agent', sa.Text, nullable=True),
        sa.Column('referrer', sa.String(500), nullable=True),
        sa.Column('method', sa.String(10), nullable=False),
        sa.Column('device_type', sa.String(50), nullable=False,
                  server_default='unknown'),
        sa.Column('language', sa.String(10), nullable=True, server_default='en'),
        sa.Column('browser', sa.String(50), nullable=True),
        sa.Column('os', sa.String(50), nullable=True),
        sa.Column('device_brand', sa.String(50), nullable=True),
        sa.Column('device_model', sa.String(50), nullable=True),
        sa.Column('ga_client_id', sa.String(100), nullable=True),
        sa.Column('ga_session_id', sa.String(100), nullable=True),
        sa.Column('gads_id', sa.String(100), nullable=True),
        sa.Column('gpi_uid', sa.String(100), nullable=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('core_user.id'), nullable=True),
    )
    op.create_index('core_pagevisit_timestamp_idx', 'core_pagevisit', ['timestamp'])
    op.create_index('core_pagevisit_device_type_idx', 'core_pagevisit', ['device_type'])
    op.create_index('core_pagevisit_ip_address_idx', 'core_pagevisit', ['ip_address'])
    op.create_table(
        'core_activationcode',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('code', sa.String(32), nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('expires_at', sa.DateTime, nullable=False),
        sa.Column('is_used', sa.Boolean, nullable=False),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('core_user.id'), nullable=False),
    )

    content_type = sa.table('django_content_type',
                            sa.column('id'), sa.column('app_label'), sa.column('model'))
    op.bulk_insert(content_type, [{'id': pk, 'app_label': app_label, 'model': model}
                                  for pk, app_label, model in CONTENT_TYPES])

    category = sa.table('core_category', sa.column('name'), sa.column('title'),
                        sa.column('title_h1'), sa.column('short_name'),
                        sa.column('slug'), sa.column('created_at'),
                        sa.column('updated_at'), sa.column('parent_category_id'))
    rows = []
    for name, title, title_h1, short_name, slug in ROOTS:
        rows.append({'name': name, 'title': title, 'title_h1': title_h1,
                     'short_name': short_name, 'slug': slug,
                     'created_at': SEEDED_AT, 'updated_at': SEEDED_AT,
                     'parent_category_id': None})
    for name, title, title_h1, short_name, slug, parent in CHILDREN:
        rows.append({'name': name, 'title': title, 'title_h1': title_h1,
                     'short_name': short_name, 'slug': slug,
                     'created_at': SEEDED_AT, 'updated_at': SEEDED_AT,
                     'parent_category_id': parent})
    op.bulk_insert(category, rows)


def downgrade():
    for name in ('core_activationcode', 'core_pagevisit', 'core_slider', 'core_message',
                 'core_comment', 'core_article_categories', 'core_article',
                 'core_category', 'authtoken_token', 'core_user',
                 'django_content_type'):
        op.drop_table(name)
