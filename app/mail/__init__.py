"""Outgoing mail: a message, a connection loader and four backends."""

from importlib import import_module

#: Every message the locmem backend accepted, in order.
outbox = []


class EmailMessage:
    def __init__(self, subject='', body='', from_email=None, to=None, bcc=None,
                 connection=None, cc=None, reply_to=None, headers=None):
        self.subject = str(subject)
        self.body = str(body)
        self.from_email = from_email
        self.to = list(to or [])
        self.cc = list(cc or [])
        self.bcc = list(bcc or [])
        self.reply_to = list(reply_to or [])
        self.extra_headers = dict(headers or {})
        self.connection = connection

    @property
    def recipients(self):
        """A property, as before -- callers must not invoke it."""
        return self.to + self.cc + self.bcc

    def message(self):
        lines = ['Subject: %s' % self.subject,
                 'From: %s' % (self.from_email or ''),
                 'To: %s' % ', '.join(self.to)]
        for key, value in self.extra_headers.items():
            lines.append('%s: %s' % (key, value))
        return '\n'.join(lines) + '\n\n' + self.body

    def get_connection(self, fail_silently=False):
        if self.connection is None:
            self.connection = get_connection(fail_silently=fail_silently)
        return self.connection

    def send(self, fail_silently=False):
        if not self.to and not self.cc and not self.bcc:
            return 0
        return self.get_connection(fail_silently).send_messages([self])


def get_connection(backend=None, fail_silently=False, **kwargs):
    """Resolve a dotted path from ``settings.EMAIL_BACKEND`` and instantiate it."""
    from app import settings
    path = backend or settings.EMAIL_BACKEND
    module_path, class_name = path.rsplit('.', 1)
    module = import_module(module_path)
    return getattr(module, class_name)(fail_silently=fail_silently, **kwargs)


def send_mail(subject, message, from_email, recipient_list, fail_silently=False,
              connection=None, html_message=None):
    """Send one message and return how many were delivered."""
    connection = connection or get_connection(fail_silently=fail_silently)
    mail = EmailMessage(subject, message, from_email, recipient_list,
                        connection=connection)
    return mail.send(fail_silently=fail_silently)
