class BaseEmailBackend:
    def __init__(self, fail_silently=False, **kwargs):
        self.fail_silently = fail_silently

    def open(self):
        pass

    def close(self):
        pass

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *args):
        self.close()

    def send_messages(self, email_messages):
        raise NotImplementedError(
            'Subclasses of BaseEmailBackend must override send_messages().')
