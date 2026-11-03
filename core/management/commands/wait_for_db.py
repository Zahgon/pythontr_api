"""Block until the database answers."""

import sys
import time


class OutputWrapper:
    def __init__(self, stream=None):
        self.stream = stream or sys.stdout

    def write(self, message, ending='\n'):
        self.stream.write(str(message) + ending)


class Style:
    def SUCCESS(self, message):
        return message

    def WARNING(self, message):
        return message


class BaseCommand:
    def __init__(self, stdout=None):
        self.stdout = OutputWrapper(stdout)
        self.style = Style()


class Command(BaseCommand):
    help = 'Django command to pause execution until database is available'

    def handle(self, *args, **options):
        if 'test' in sys.argv:
            return
        from app.db import connections
        self.stdout.write('Waiting for database...')
        db_conn = None
        while not db_conn:
            try:
                connections['default'].ensure_connection()
                db_conn = True
            except Exception:
                self.stdout.write('Database unavailable, waiting 1 second...')
                time.sleep(1)
        self.stdout.write(self.style.SUCCESS('Database available!'))


if __name__ == '__main__':
    Command().handle()
