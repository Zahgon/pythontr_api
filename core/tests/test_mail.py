import smtplib
import unittest
from io import StringIO

from flask import current_app

from app import mail
from app.custom_email_backend import CustomEmailBackend


class FakeSMTP:
    """Stands in for ``smtplib.SMTP`` so no socket is opened."""

    instances = []

    def __init__(self, host, port, timeout=None):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.started_tls = False
        self.tls_context = None
        self.login_args = None
        self.sent = []
        self.quit_called = False
        self.closed = False
        FakeSMTP.instances.append(self)

    def starttls(self, context=None):
        self.started_tls = True
        self.tls_context = context

    def login(self, username, password):
        self.login_args = (username, password)

    def sendmail(self, from_email, recipients, message):
        self.sent.append((from_email, recipients, message))

    def quit(self):
        self.quit_called = True

    def close(self):
        self.closed = True


class BrokenSMTP(FakeSMTP):

    def sendmail(self, from_email, recipients, message):
        raise smtplib.SMTPException('refused')


class UnreachableSMTP(FakeSMTP):

    def __init__(self, host, port, timeout=None):
        raise OSError('unreachable')


class DisconnectingSMTP(FakeSMTP):

    def quit(self):
        raise smtplib.SMTPServerDisconnected('gone')


class QuitFailingSMTP(FakeSMTP):

    def quit(self):
        raise smtplib.SMTPException('refused')


def message(to=None, subject='Konu', body='Gövde'):
    return mail.EmailMessage(
        subject=subject,
        body=body,
        from_email='noreply@pythontr.com',
        to=['reader@example.com'] if to is None else to,
    )


class EmailMessageTests(unittest.TestCase):

    def setUp(self):
        FakeSMTP.instances = []
        del mail.outbox[:]

    def test_recipients(self):
        self.assertEqual(message().recipients(), ['reader@example.com'])

    def test_message_headers(self):
        built = message().message()

        self.assertEqual(built['To'], 'reader@example.com')
        self.assertEqual(built['From'], 'noreply@pythontr.com')
        self.assertIn('Date', built)
        self.assertIn('Message-ID', built)

    def test_message_encodes_non_ascii_subject(self):
        built = message(subject='Şifre sıfırlama').message()

        self.assertEqual(built['Subject'], 'Şifre sıfırlama')
        self.assertIn(b'=?utf-8?', built.as_bytes())
        self.assertEqual(built.get_payload(decode=True).decode('utf-8'),
                         'Gövde')

    def test_extra_headers_are_added(self):
        outgoing = message()
        outgoing.extra_headers = {
            'From': 'other@pythontr.com',
            'To': 'ignored@example.com',
            'Reply-To': 'reply@pythontr.com',
        }
        built = outgoing.message()

        self.assertEqual(built['From'], 'other@pythontr.com')
        self.assertEqual(built['To'], 'reader@example.com')
        self.assertEqual(built['Reply-To'], 'reply@pythontr.com')

    def test_send_without_recipients_sends_nothing(self):
        self.assertEqual(message(to=[]).send(), 0)

    def test_send_uses_the_configured_backend(self):
        outgoing = message()
        outgoing.connection = mail.LocmemEmailBackend()

        self.assertEqual(outgoing.send(), 1)
        self.assertEqual(len(mail.outbox), 1)


class BaseBackendTests(unittest.TestCase):

    def test_send_messages_must_be_overridden(self):
        with self.assertRaises(NotImplementedError):
            mail.BaseEmailBackend().send_messages([message()])

    def test_context_manager_opens_and_closes(self):
        backend = mail.LocmemEmailBackend()

        with backend as opened:
            self.assertIs(opened, backend)

    def test_context_manager_closes_when_open_fails(self):
        closed = []

        class Failing(mail.BaseEmailBackend):

            def open(self):
                raise OSError('nope')

            def close(self):
                closed.append(True)

        with self.assertRaises(OSError):
            with Failing():
                pass
        self.assertEqual(closed, [True])


class LocmemBackendTests(unittest.TestCase):

    def setUp(self):
        del mail.outbox[:]

    def test_messages_are_collected(self):
        sent = mail.LocmemEmailBackend().send_messages(
            [message(), message(to=['other@example.com'])]
        )

        self.assertEqual(sent, 2)
        self.assertEqual(len(mail.outbox), 2)


class ConsoleBackendTests(unittest.TestCase):

    def test_message_is_written_to_the_stream(self):
        stream = StringIO()

        sent = mail.ConsoleEmailBackend(stream=stream).send_messages(
            [message()]
        )

        self.assertEqual(sent, 1)
        self.assertIn('reader@example.com', stream.getvalue())
        self.assertIn('-' * 79, stream.getvalue())

    def test_no_messages_writes_nothing(self):
        stream = StringIO()

        sent = mail.ConsoleEmailBackend(stream=stream).send_messages([])

        self.assertEqual(sent, 0)
        self.assertEqual(stream.getvalue(), '')

    def test_write_failure_is_raised(self):
        class Broken(StringIO):

            def write(self, value):
                raise OSError('closed')

        backend = mail.ConsoleEmailBackend(stream=Broken())

        with self.assertRaises(OSError):
            backend.send_messages([message()])

    def test_write_failure_is_swallowed_when_silent(self):
        class Broken(StringIO):

            def write(self, value):
                raise OSError('closed')

        backend = mail.ConsoleEmailBackend(stream=Broken(),
                                           fail_silently=True)

        self.assertEqual(backend.send_messages([message()]), 0)


class DummyBackendTests(unittest.TestCase):

    def test_messages_are_counted_but_discarded(self):
        self.assertEqual(
            mail.DummyEmailBackend().send_messages([message(), message()]), 2
        )


class SMTPBackendTests(unittest.TestCase):

    def setUp(self):
        FakeSMTP.instances = []

    def backend(self, connection_class=FakeSMTP, **kwargs):
        kwargs.setdefault('host', 'smtp.example.com')
        kwargs.setdefault('port', 587)
        kwargs.setdefault('username', 'user')
        kwargs.setdefault('password', 'secret')
        kwargs.setdefault('use_tls', True)
        backend = mail.SMTPEmailBackend(**kwargs)
        backend.connection_class = connection_class
        return backend

    def test_settings_supply_the_defaults(self):
        backend = mail.SMTPEmailBackend()
        config = current_app.config

        self.assertEqual(backend.host, config.get('MAIL_SERVER'))
        self.assertEqual(backend.port, config.get('MAIL_PORT'))
        self.assertEqual(backend.username, config.get('MAIL_USERNAME'))

    def test_open_starts_tls_and_logs_in(self):
        backend = self.backend()

        self.assertTrue(backend.open())
        connection = FakeSMTP.instances[0]
        self.assertTrue(connection.started_tls)
        self.assertEqual(connection.login_args, ('user', 'secret'))

    def test_open_is_a_no_op_when_already_connected(self):
        backend = self.backend()
        backend.open()

        self.assertFalse(backend.open())
        self.assertEqual(len(FakeSMTP.instances), 1)

    def test_open_raises_when_the_host_is_unreachable(self):
        backend = self.backend(connection_class=UnreachableSMTP)

        with self.assertRaises(OSError):
            backend.open()

    def test_open_returns_none_when_silent(self):
        backend = self.backend(connection_class=UnreachableSMTP,
                               fail_silently=True)

        self.assertIsNone(backend.open())

    def test_close_quits_the_connection(self):
        backend = self.backend()
        backend.open()
        connection = FakeSMTP.instances[0]

        backend.close()

        self.assertTrue(connection.quit_called)
        self.assertIsNone(backend.connection)

    def test_close_without_a_connection_does_nothing(self):
        backend = self.backend()

        backend.close()

        self.assertIsNone(backend.connection)

    def test_close_falls_back_to_closing_a_dropped_connection(self):
        backend = self.backend(connection_class=DisconnectingSMTP)
        backend.open()
        connection = FakeSMTP.instances[0]

        backend.close()

        self.assertTrue(connection.closed)

    def test_close_swallows_a_refused_quit_when_silent(self):
        backend = self.backend(connection_class=QuitFailingSMTP,
                               fail_silently=True)
        backend.open()

        backend.close()

        self.assertIsNone(backend.connection)

    def test_send_messages_delivers_and_closes(self):
        backend = self.backend()

        sent = backend.send_messages([message()])

        self.assertEqual(sent, 1)
        connection = FakeSMTP.instances[0]
        self.assertEqual(len(connection.sent), 1)
        self.assertTrue(connection.quit_called)

    def test_send_messages_without_messages(self):
        self.assertEqual(self.backend().send_messages([]), 0)

    def test_send_messages_keeps_an_already_open_connection(self):
        backend = self.backend()
        backend.open()

        backend.send_messages([message()])

        self.assertFalse(FakeSMTP.instances[0].quit_called)

    def test_send_messages_returns_zero_when_open_fails_silently(self):
        backend = self.backend(connection_class=UnreachableSMTP,
                               fail_silently=True)

        self.assertEqual(backend.send_messages([message()]), 0)

    def test_send_messages_raises_when_open_fails(self):
        backend = self.backend(connection_class=UnreachableSMTP)

        with self.assertRaises(OSError):
            backend.send_messages([message()])

    def test_message_without_recipients_is_skipped(self):
        backend = self.backend()

        self.assertEqual(backend.send_messages([message(to=[])]), 0)

    def test_refused_message_raises(self):
        backend = self.backend(connection_class=BrokenSMTP)

        with self.assertRaises(smtplib.SMTPException):
            backend.send_messages([message()])

    def test_refused_message_is_counted_out_when_silent(self):
        backend = self.backend(connection_class=BrokenSMTP,
                               fail_silently=True)

        self.assertEqual(backend.send_messages([message()]), 0)


class CustomEmailBackendTests(unittest.TestCase):

    def setUp(self):
        FakeSMTP.instances = []

    def backend(self, connection_class=FakeSMTP, **kwargs):
        kwargs.setdefault('host', 'smtp.example.com')
        kwargs.setdefault('port', 587)
        kwargs.setdefault('username', 'user')
        kwargs.setdefault('password', 'secret')
        kwargs.setdefault('use_tls', True)
        backend = CustomEmailBackend(**kwargs)
        backend.connection_class = connection_class
        return backend

    def test_open_hands_a_relaxed_context_to_starttls(self):
        backend = self.backend()

        self.assertTrue(backend.open())
        connection = FakeSMTP.instances[0]
        self.assertIsNotNone(connection.tls_context)
        self.assertFalse(connection.tls_context.check_hostname)
        self.assertEqual(connection.login_args, ('user', 'secret'))

    def test_open_returns_the_existing_connection(self):
        backend = self.backend()
        backend.open()

        self.assertIs(backend.open(), backend.connection)

    def test_open_raises_when_the_host_is_unreachable(self):
        backend = self.backend(connection_class=UnreachableSMTP)

        with self.assertRaises(OSError):
            backend.open()

    def test_open_returns_false_when_silent(self):
        backend = self.backend(connection_class=UnreachableSMTP,
                               fail_silently=True)

        self.assertFalse(backend.open())


class GetConnectionTests(unittest.TestCase):

    def test_short_names_are_accepted(self):
        self.assertIsInstance(
            mail.get_connection('locmem'), mail.LocmemEmailBackend
        )
        self.assertIsInstance(
            mail.get_connection('console'), mail.ConsoleEmailBackend
        )
        self.assertIsInstance(
            mail.get_connection('dummy'), mail.DummyEmailBackend
        )

    def test_the_previous_dotted_paths_still_resolve(self):
        self.assertIsInstance(
            mail.get_connection('django.core.mail.backends.smtp.EmailBackend'),
            mail.SMTPEmailBackend,
        )

    def test_an_unknown_path_is_imported(self):
        connection = mail.get_connection(
            'app.custom_email_backend.CustomEmailBackend'
        )

        self.assertIsInstance(connection, CustomEmailBackend)

    def test_the_configuration_supplies_the_default(self):
        self.assertIsInstance(
            mail.get_connection(), mail.LocmemEmailBackend
        )


class SendMailTests(unittest.TestCase):

    def setUp(self):
        del mail.outbox[:]

    def test_message_is_delivered(self):
        sent = mail.send_mail(
            'Konu',
            'Gövde',
            'noreply@pythontr.com',
            ['reader@example.com'],
        )

        self.assertEqual(sent, 1)
        self.assertEqual(mail.outbox[0].subject, 'Konu')
        self.assertEqual(mail.outbox[0].recipients(), ['reader@example.com'])

    def test_an_explicit_connection_is_used(self):
        connection = mail.DummyEmailBackend()

        sent = mail.send_mail(
            'Konu',
            'Gövde',
            'noreply@pythontr.com',
            ['reader@example.com'],
            connection=connection,
        )

        self.assertEqual(sent, 1)
        self.assertEqual(mail.outbox, [])
