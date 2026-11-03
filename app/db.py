"""Database access: one SQLAlchemy 2 engine, one session per request.

A session is opened by :class:`app.middleware.SessionMiddleware` when a request arrives and
closed when the response has been written, so no identity map and no pending state is ever
shared between two requests.
"""

import os

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Django wrote the primary keys of the five oldest tables as 32-bit and the four newest as
# 64-bit. The widths are part of the schema, so they are named rather than guessed.
BIG_PK = 'BIGINT'


class Base(DeclarativeBase):
    """Declarative base. Importing :mod:`core.models` registers every table on it."""


def build_url(config=None):
    """Build a SQLAlchemy URL from a ``DATABASES['default']``-shaped mapping."""
    if config is None:
        from app import settings
        config = settings.DATABASES['default']
    engine = (config.get('ENGINE') or '').strip()
    name = config.get('NAME') or ''
    if 'sqlite' in engine or engine == '':
        if name in ('', ':memory:'):
            return 'sqlite+pysqlite:///:memory:'
        return 'sqlite+pysqlite:///%s' % name
    user = config.get('USER') or ''
    password = config.get('PASSWORD') or ''
    # Host and port are passed through as configured, as the original's DATABASES did: an
    # unset value is omitted from the authority so the driver applies its own default,
    # rather than naming one here.
    host = config.get('HOST') or ''
    port = config.get('PORT') or ''
    credentials = user
    if password:
        credentials = '%s:%s' % (user, password)
    if credentials:
        credentials += '@'
    authority = '%s:%s' % (host, port) if port else host
    return 'postgresql+psycopg2://%s%s/%s' % (credentials, authority, name)


_engine = None
_sessionmaker = None


def get_engine():
    global _engine, _sessionmaker
    if _engine is None:
        url = os.environ.get('DATABASE_URL') or build_url()
        kwargs = {'future': True, 'echo': False}
        if url.startswith('sqlite'):
            kwargs['connect_args'] = {'check_same_thread': False}
        _engine = create_engine(url, **kwargs)
        _sessionmaker = sessionmaker(bind=_engine, autoflush=False,
                                     expire_on_commit=False, future=True)
    return _engine


def reset_engine():
    """Drop the cached engine, so a later call reads the environment again."""
    global _engine, _sessionmaker
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _sessionmaker = None


def new_session():
    get_engine()
    return _sessionmaker()


def create_all():
    import core.models  # noqa: F401  (registers every table on Base)
    Base.metadata.create_all(get_engine())


def drop_all():
    import core.models  # noqa: F401
    Base.metadata.drop_all(get_engine())


class _DefaultConnection:
    """``connections['default']`` as ``wait_for_db`` used it."""

    def ensure_connection(self):
        with get_engine().connect() as connection:
            connection.execute(text('SELECT 1'))


connections = {'default': _DefaultConnection()}
