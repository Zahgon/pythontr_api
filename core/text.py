"""Text helpers ported from ``django.utils.text``.

Slugs are part of the public API of this project (articles and categories are
addressable by slug), so the slugify implementation has to behave exactly like
the one the Django version used.
"""
import re
import unicodedata


def slugify(value, allow_unicode=False):
    """Port of ``django.utils.text.slugify``."""
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize('NFKC', value)
    else:
        value = (
            unicodedata.normalize('NFKD', value)
            .encode('ascii', 'ignore')
            .decode('ascii')
        )
    value = re.sub(r'[^\w\s-]', '', value.lower())
    return re.sub(r'[-\s]+', '-', value).strip('-_')
