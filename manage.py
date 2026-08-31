#!/usr/bin/env python
"""Command-line utility for administrative tasks."""
from flask.cli import FlaskGroup

from app import create_app

cli = FlaskGroup(create_app=create_app)


def main():
    """Run administrative tasks."""
    cli.main()


if __name__ == '__main__':
    main()
