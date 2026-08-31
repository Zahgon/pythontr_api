"""Filesystem storage for uploaded images.

Django's ``FileField`` wrote relative paths below ``MEDIA_ROOT`` (which this
project never set, so the effective root is the project directory) and appended
a random suffix when a name was already taken.  Both behaviours are reproduced
here because the stored strings are served back to clients verbatim through the
``image`` / ``image_url`` fields.
"""
import os
import pathlib

from core.hashers import get_random_string

ALPHANUMERIC = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'


def media_root():
    from flask import current_app
    return pathlib.Path(current_app.config['BASE_DIR'])


def get_available_name(name):
    """Append ``_<7 random chars>`` until the name is free (Django's rule)."""
    root = media_root()
    dir_name, file_name = os.path.split(name)
    stem, ext = os.path.splitext(file_name)
    while (root / name).exists():
        name = os.path.join(
            dir_name,
            '%s_%s%s' % (stem, get_random_string(7, ALPHANUMERIC), ext),
        )
    return name


def save(name, content):
    """Persist ``content`` (a file object or bytes), return its name."""
    name = get_available_name(name)
    target = media_root() / name
    target.parent.mkdir(parents=True, exist_ok=True)
    data = content if isinstance(content, bytes) else content.read()
    if isinstance(data, str):
        data = data.encode()
    with open(target, 'wb') as handle:
        handle.write(data)
    return name


def move(old_name, new_name):
    """Relocate an already stored file, returning the name actually used."""
    root = media_root()
    source = root / old_name
    if not source.exists():
        return old_name
    new_name = get_available_name(new_name)
    target = root / new_name
    target.parent.mkdir(parents=True, exist_ok=True)
    os.replace(source, target)
    return new_name


class ContentFile:
    """An in-memory upload, the stand-in for Django's ``ContentFile``."""

    def __init__(self, content, name=None):
        self.content = content
        self.name = name

    def read(self):
        return self.content


def persist(instance, value, upload_to):
    """Store a freshly uploaded file and return the name to keep in the column.

    Values that are already names are handed straight back, which is what makes
    it safe to call on every save.
    """
    if value is None or isinstance(value, str):
        return value
    name = getattr(value, 'filename', None) or getattr(value, 'name', '') or ''
    return save(upload_to(instance, name), value)


def delete(name):
    if not name:
        return
    target = media_root() / name
    if target.exists():
        target.unlink()
