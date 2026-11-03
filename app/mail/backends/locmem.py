from app import mail
from app.mail.backends.base import BaseEmailBackend


class EmailBackend(BaseEmailBackend):
    """Collects messages in ``app.mail.outbox`` instead of delivering them."""

    def send_messages(self, email_messages):
        messages = list(email_messages)
        for message in messages:
            message.message()  # fail here rather than at read time
            mail.outbox.append(message)
        return len(messages)
