import sys
import threading

from app.mail.backends.base import BaseEmailBackend


class EmailBackend(BaseEmailBackend):
    def __init__(self, *args, stream=None, **kwargs):
        self.stream = stream or sys.stdout
        self._lock = threading.RLock()
        super().__init__(*args, **kwargs)

    def write_message(self, message):
        self.stream.write('%s\n' % message.message())
        # `recipients` is a property on the message, so it is read, never called.
        self.stream.write('-' * 79)
        self.stream.write('\n')

    def send_messages(self, email_messages):
        messages = list(email_messages)
        if not messages:
            return 0
        with self._lock:
            try:
                for message in messages:
                    self.write_message(message)
                    self.stream.flush()
            except Exception:
                if not self.fail_silently:
                    raise
                return 0
        return len(messages)
