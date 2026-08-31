import time
import click
from flask import current_app
from flask.cli import with_appcontext
from sqlalchemy.exc import OperationalError
from psycopg2 import OperationalError as Psycopg2Error

from app.extensions import db


class Connection(object):
    """A single database alias with the ``ensure_connection`` contract."""

    def __init__(self, alias):
        self.alias = alias

    def ensure_connection(self):
        db.engine.connect().close()


class ConnectionHandler(object):
    """``connections["default"]`` lookup; the command reads unchanged."""

    def __getitem__(self, alias):
        return Connection(alias)


connections = ConnectionHandler()


def wait_for_db(stdout=click.echo):
    stdout('Waiting for database...')
    connected = False
    while not connected:
        try:
            db_conn = connections["default"]
            if not current_app.config.get('TESTING'):
                db_conn.ensure_connection()
            stdout('Database is ready!...')
            connected = True
        except (OperationalError, Psycopg2Error):
            stdout('Database unavailable, waiting 1 second...')
            time.sleep(1)

    stdout(click.style('Database available!', fg='green'))


@click.command('wait-for-db')
@with_appcontext
def wait_for_db_command():
    """Block until the configured database accepts connections."""
    wait_for_db()


def register(app):
    app.cli.add_command(wait_for_db_command)
