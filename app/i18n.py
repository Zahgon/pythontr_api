"""Translation.

The repository ships ``locale/tr`` and ``locale/en`` as ``.po`` sources only; no compiled
catalogue was ever added to the tree, so under Django every project message key travelled
to the client unchanged. That is reproduced here: :func:`gettext` returns its argument.

The framework vocabulary is different. Django REST Framework shipped a compiled Turkish
catalogue, so its own messages did reach the client in Turkish. Those strings have no
catalogue to come from any more, so they are written out literally in :mod:`app.wire` and
:mod:`app.parsing` instead of being looked up.
"""


class LazyString:
    """A string that renders only when it is used, as ``gettext_lazy`` returned."""

    __slots__ = ('_key',)

    def __init__(self, key):
        self._key = key

    def __str__(self):
        return gettext(self._key)

    def __eq__(self, other):
        return str(self) == str(other)

    def __hash__(self):
        return hash(str(self))

    def __repr__(self):
        return repr(str(self))

    def format(self, *args, **kwargs):
        return str(self).format(*args, **kwargs)


def gettext(message):
    """Return ``message``. No compiled catalogue exists, so nothing is translated."""
    if isinstance(message, LazyString):
        return str(message)
    return message


def gettext_lazy(message):
    return LazyString(message)


def ngettext(singular, plural, number):
    return gettext(singular if number == 1 else plural)
