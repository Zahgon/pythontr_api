from unittest import TestCase
from unittest.mock import patch

from sqlalchemy.exc import OperationalError

from core.cli import wait_for_db


def operational_error():
    """The driver error the command waits on, built with its required args."""
    return OperationalError('SELECT 1', {}, Exception('database unavailable'))


class CommandTests(TestCase):

    @patch('core.cli.ConnectionHandler.__getitem__')
    def test_wait_for_db_ready(self, gi):
        """Test waiting for db when db is available"""
        gi.return_value = True
        wait_for_db()
        self.assertEqual(gi.call_count, 1)

    @patch('time.sleep', return_value=True)
    @patch('core.cli.ConnectionHandler.__getitem__')
    def test_wait_for_db(self, gi, ts):
        """Test waiting for db"""
        gi.side_effect = [operational_error()] * 5 + [True]
        wait_for_db()
        self.assertEqual(gi.call_count, 6)
