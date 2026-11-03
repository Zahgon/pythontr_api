"""Text helpers the models and the file-path builders used to take from Django."""

import re
import unicodedata


def slugify(value, allow_unicode=False):
    """ASCII slug, byte compatible with the slugs already stored in the database."""
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize('NFKC', value)
    else:
        value = (unicodedata.normalize('NFKD', value)
                 .encode('ascii', 'ignore').decode('ascii'))
    value = re.sub(r'[^\w\s-]', '', value.lower())
    return re.sub(r'[-\s]+', '-', value).strip('-_')


def capfirst(value):
    return value and str(value)[0].upper() + str(value)[1:]


def get_text_list(items, last_word='or'):
    items = [str(item) for item in items]
    if not items:
        return ''
    if len(items) == 1:
        return items[0]
    return '%s %s %s' % (', '.join(items[:-1]), last_word, items[-1])
