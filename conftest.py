"""Shared test setup.

The previous test runner created a throwaway database, applied the migrations
to it and handed every test a clean copy.  That is reproduced here: the
migrations run once into a template file and each test works against its own
copy, so the seeded rows the migrations insert are present and no test can see
another test's writes.

Setting ``TEST_DATABASE_URL`` runs the same suite against a server instead --
the deployment engine is PostgreSQL, and copying a file is not available
there.  That path creates a throwaway database next to the named one,
migrates it once, and gives each test a transaction that is rolled back
afterwards, which is how the previous runner isolated tests too.
"""
import os
import shutil

import pytest
import sqlalchemy as sa

# Settings are selected at import time, and several modules decide what to
# declare based on that choice, so the flag has to be set before the first
# application import.
os.environ['FLASK_TESTING'] = 'true'
os.environ.setdefault('ALLOW_HOST', 'localhost,testserver')
os.environ.setdefault('DEBUG', 'True')
os.environ.setdefault('SITE_URL', 'http://testserver')
os.environ.setdefault('EMAIL_BACKEND', 'locmem')
os.environ.setdefault('DEFAULT_FROM_EMAIL', 'noreply@pythontr.com')

SERVER_URL = os.environ.get('TEST_DATABASE_URL') or None

from app import create_app  # noqa: E402
from app.api.test import APIClient, Client  # noqa: E402
from app.extensions import db  # noqa: E402


application = create_app()
application.testing = True
application.config['SERVER_NAME'] = 'testserver'
# The API tests build their URLs at module import time, the way they always
# have.  Doing that needs an application context, and conftest is imported
# before any test module, so the context is pushed here and left in place.
application.app_context().push()


@pytest.fixture(scope='session')
def app(tmp_path_factory):
    if SERVER_URL is None:
        template = tmp_path_factory.mktemp('database') / 'template.sqlite3'
        _migrate(application, sa.create_engine(_sqlite_url(template)))
        application.template_database = str(template)
        yield application
        return
    url = _create_server_database(SERVER_URL)
    engine = sa.create_engine(url)
    _migrate(application, engine)
    application.server_engine = engine
    yield application
    engine.dispose()
    _drop_server_database(SERVER_URL)


def _sqlite_url(path):
    return 'sqlite:///{}'.format(path)


def _test_url(url):
    parsed = sa.engine.make_url(url)
    return parsed.set(database='test_{}'.format(parsed.database))


def _maintenance_engine(url):
    parsed = sa.engine.make_url(url)
    return sa.create_engine(
        parsed.set(database='postgres'), isolation_level='AUTOCOMMIT',
    )


def _create_server_database(url):
    target = _test_url(url)
    engine = _maintenance_engine(url)
    with engine.connect() as connection:
        connection.exec_driver_sql(
            'DROP DATABASE IF EXISTS "{}"'.format(target.database),
        )
        connection.exec_driver_sql(
            'CREATE DATABASE "{}"'.format(target.database),
        )
    engine.dispose()
    return target


def _drop_server_database(url):
    target = _test_url(url)
    engine = _maintenance_engine(url)
    with engine.connect() as connection:
        connection.exec_driver_sql(
            'DROP DATABASE IF EXISTS "{}"'.format(target.database),
        )
    engine.dispose()


def _migrate(application, engine):
    from flask_migrate import upgrade

    with application.app_context():
        db.engines[None] = engine
        upgrade()
        db.session.remove()
    engine.dispose()


@pytest.fixture(autouse=True)
def database(app, tmp_path):
    if SERVER_URL is None:
        path = tmp_path / 'test.sqlite3'
        shutil.copyfile(app.template_database, path)
        engine = sa.create_engine(_sqlite_url(path))
        with app.app_context():
            db.engines[None] = engine
            db.session.remove()
            yield db
            db.session.remove()
        engine.dispose()
        return
    connection = app.server_engine.connect()
    transaction = connection.begin()
    with app.app_context():
        # The session is bound to an open connection rather than to the
        # engine, so the commits the application makes land inside this
        # transaction and the rollback below undoes every one of them.
        db.engines[None] = connection
        db.session.remove()
        yield db
        db.session.remove()
    if transaction.is_active:
        transaction.rollback()
    connection.close()


@pytest.fixture
def client(app):
    return Client(app)


@pytest.fixture
def api_client(app):
    return APIClient(app)
