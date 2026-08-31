"""Outgoing mail.

The project selects its mail transport at runtime through the ``EMAIL_BACKEND``
environment variable, and one of the values it is deployed with is a backend
that lives in this repository (``app.custom_email_backend``).  That backend
overrides ``open()`` to hand a relaxed SSL context to ``starttls()``, so the
backend contract it overrides -- ``open()`` / ``close()`` / ``send_messages()``
plus ``fail_silently`` -- is part of what has to survive the migration, not an
implementation detail of the framework being left behind.  It is therefore
reproduced here rather than replaced with a transport that has no equivalent
hook.

``send_mail()`` keeps the same signature and the same return value (the number
of messages successfully delivered) that the views already rely on, and lets
``smtplib.SMTPException`` escape so the views' error handling still fires.
"""

import smtplib
import sys
import threading
from email.header import Header
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid

from flask import current_app

DEFAULT_CHARSET = 'utf-8'

# Every message the local memory backend has been handed, in order.  Tests read
# this the same way they used to read the framework's own test outbox.
outbox = []


class EmailMessage:
    """A single outgoing message."""

    def __init__(self, subject='', body='', from_email=None, to=None,
                 connection=None):
        self.subject = subject
        self.body = body
        self.from_email = from_email
        self.to = list(to) if to else []
        self.connection = connection
        self.extra_headers = {}

    def recipients(self):
        return self.to

    def message(self):
        msg = MIMEText(self.body, 'plain', DEFAULT_CHARSET)
        msg['Subject'] = Header(self.subject, DEFAULT_CHARSET)
        msg['From'] = self.extra_headers.get('From', self.from_email)
        msg['To'] = ', '.join(self.to)
        msg['Date'] = formatdate()
        msg['Message-ID'] = make_msgid()
        for name, value in self.extra_headers.items():
            if name.lower() in ('from', 'to'):
                continue
            msg[name] = value
        return msg

    def send(self, fail_silently=False):
        if not self.recipients():
            return 0
        connection = self.connection or get_connection(
            fail_silently=fail_silently)
        return connection.send_messages([self])


class BaseEmailBackend:

    def __init__(self, fail_silently=False, **kwargs):
        self.fail_silently = fail_silently

    def open(self):
        pass

    def close(self):
        pass

    def __enter__(self):
        try:
            self.open()
        except Exception:
            self.close()
            raise
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def send_messages(self, email_messages):
        raise NotImplementedError(
            'subclasses of BaseEmailBackend must override send_messages()')


class SMTPEmailBackend(BaseEmailBackend):

    connection_class = smtplib.SMTP

    def __init__(self, host=None, port=None, username=None, password=None,
                 use_tls=None, fail_silently=False, timeout=None, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)
        config = current_app.config
        self.host = host if host is not None else config.get('MAIL_SERVER')
        self.port = port if port is not None else config.get('MAIL_PORT')
        self.username = username if username is not None \
            else config.get('MAIL_USERNAME')
        self.password = password if password is not None \
            else config.get('MAIL_PASSWORD')
        self.use_tls = use_tls if use_tls is not None \
            else config.get('MAIL_USE_TLS')
        self.timeout = timeout
        self.connection = None
        self._lock = threading.RLock()

    def open(self):
        if self.connection:
            return False
        try:
            self.connection = self.connection_class(
                self.host, self.port, timeout=self.timeout
            )
            if self.use_tls:
                self.connection.starttls()
            if self.username and self.password:
                self.connection.login(self.username, self.password)
            return True
        except OSError:
            if not self.fail_silently:
                raise

    def close(self):
        if self.connection is None:
            return
        try:
            self.connection.quit()
        except (smtplib.SMTPServerDisconnected, OSError):
            self.connection.close()
        except smtplib.SMTPException:
            if not self.fail_silently:
                raise
        finally:
            self.connection = None

    def send_messages(self, email_messages):
        if not email_messages:
            return 0
        with self._lock:
            new_connection = self.connection is None
            try:
                opened = self.open()
            except Exception:
                if not self.fail_silently:
                    raise
                return 0
            if not self.connection or (new_connection and not opened):
                return 0
            sent = 0
            for message in email_messages:
                if self._send(message):
                    sent += 1
            if new_connection:
                self.close()
        return sent

    def _send(self, email_message):
        recipients = email_message.recipients()
        if not recipients:
            return False
        message = email_message.message()
        # SMTP wants CRLF line endings, and the default policy writes LF.
        policy = message.policy.clone(linesep='\r\n')
        try:
            self.connection.sendmail(
                email_message.from_email,
                recipients,
                message.as_bytes(policy=policy),
            )
        except smtplib.SMTPException:
            if not self.fail_silently:
                raise
            return False
        return True


class ConsoleEmailBackend(BaseEmailBackend):

    def __init__(self, *args, **kwargs):
        self.stream = kwargs.pop('stream', None) or sys.stdout
        super().__init__(*args, **kwargs)
        self._lock = threading.RLock()

    def send_messages(self, email_messages):
        if not email_messages:
            return 0
        sent = 0
        with self._lock:
            try:
                for message in email_messages:
                    self.stream.write('%s\n' % message.message().as_string())
                    self.stream.write('-' * 79)
                    self.stream.write('\n')
                    self.stream.flush()
                    sent += 1
            except Exception:
                if not self.fail_silently:
                    raise
                return sent
        return sent


class LocmemEmailBackend(BaseEmailBackend):

    def send_messages(self, email_messages):
        sent = 0
        for message in email_messages:
            message.message()
            outbox.append(message)
            sent += 1
        return sent


class DummyEmailBackend(BaseEmailBackend):

    def send_messages(self, email_messages):
        return len(list(email_messages))


# The environment variable this project is deployed with holds the dotted path
# of the backend that used to implement each transport.  Those paths stay
# valid so existing .env files, compose files and deploy scripts keep working.
BACKEND_ALIASES = {
    'django.core.mail.backends.smtp.EmailBackend': SMTPEmailBackend,
    'django.core.mail.backends.console.EmailBackend': ConsoleEmailBackend,
    'django.core.mail.backends.locmem.EmailBackend': LocmemEmailBackend,
    'django.core.mail.backends.dummy.EmailBackend': DummyEmailBackend,
    'smtp': SMTPEmailBackend,
    'console': ConsoleEmailBackend,
    'locmem': LocmemEmailBackend,
    'dummy': DummyEmailBackend,
}


def get_connection(backend=None, fail_silently=False, **kwargs):
    path = backend or current_app.config['MAIL_BACKEND']
    backend_class = BACKEND_ALIASES.get(path)
    if backend_class is None:
        from werkzeug.utils import import_string
        backend_class = import_string(path)
    return backend_class(fail_silently=fail_silently, **kwargs)


def send_mail(subject, message, from_email, recipient_list,
              fail_silently=False, connection=None):
    connection = connection or get_connection(fail_silently=fail_silently)
    mail = EmailMessage(
        subject=subject,
        body=message,
        from_email=from_email,
        to=recipient_list,
        connection=connection,
    )
    return mail.send()
