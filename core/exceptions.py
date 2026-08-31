"""Errors the ORM layer raises for programming mistakes.

These are not API exceptions: nothing catches them, so they surface as a
500 exactly like their Django counterparts did.
"""


class FieldError(Exception):
    """A query referenced a field the model does not define."""


class ImproperlyConfigured(Exception):
    """A serializer or view is misconfigured."""
