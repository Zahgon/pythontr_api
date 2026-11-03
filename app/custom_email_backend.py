import ssl

from app.mail.backends.smtp import EmailBackend


class CustomEmailBackend(EmailBackend):
    """Deployed behaviour: TLS with hostname checking and verification switched off."""

    def ssl_context(self):
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        return context
