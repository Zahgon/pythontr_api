import smtplib
import ssl
import threading

from app.mail.backends.base import BaseEmailBackend


class EmailBackend(BaseEmailBackend):
    def __init__(self, host=None, port=None, username=None, password=None,
                 use_tls=None, fail_silently=False, timeout=None, **kwargs):
        from app import settings
        super().__init__(fail_silently=fail_silently)
        self.host = host if host is not None else settings.EMAIL_HOST
        self.port = port if port is not None else settings.EMAIL_PORT
        self.username = username if username is not None else settings.EMAIL_HOST_USER
        self.password = (password if password is not None
                         else settings.EMAIL_HOST_PASSWORD)
        self.use_tls = use_tls if use_tls is not None else settings.EMAIL_USE_TLS
        self.timeout = timeout
        self.connection = None
        self._lock = threading.RLock()

    def ssl_context(self):
        return ssl.create_default_context()

    def open(self):
        if self.connection is not None:
            return False
        connection = None
        try:
            connection = smtplib.SMTP(self.host, self.port, timeout=self.timeout)
            if self.use_tls:
                connection.starttls(context=self.ssl_context())
            if self.username and self.password:
                connection.login(self.username, self.password)
        except OSError:
            # The socket is already open once SMTP() returns, so a failure in starttls or
            # login has to release it before the handle goes out of scope.
            if connection is not None:
                connection.close()
            if not self.fail_silently:
                raise
            return False
        except BaseException:
            # Anything else -- a credential that will not encode, for instance -- is not part
            # of the fail_silently contract, so it propagates, but the socket is still ours.
            if connection is not None:
                connection.close()
            raise
        self.connection = connection
        return True

    def close(self):
        if self.connection is None:
            return
        try:
            self.connection.quit()
        except (smtplib.SMTPException, OSError):
            # quit() can fail with the socket still open, so release it explicitly.
            self.connection.close()
            if not self.fail_silently:
                raise
        finally:
            self.connection = None

    def send_messages(self, email_messages):
        messages = list(email_messages)
        if not messages:
            return 0
        with self._lock:
            opened = self.open()
            if self.connection is None:
                return 0
            sent = 0
            try:
                for message in messages:
                    try:
                        self.connection.sendmail(message.from_email, message.recipients,
                                                 message.message().encode('utf-8'))
                    except smtplib.SMTPException:
                        if not self.fail_silently:
                            raise
                        continue
                    sent += 1
            finally:
                if opened:
                    self.close()
        return sent
