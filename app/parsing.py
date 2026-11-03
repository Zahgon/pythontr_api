"""Request bodies and field errors.

Mutating routes read and validate the raw body themselves, so a bad request is a 400 with
a field-keyed body, never a framework-shaped 422.
"""

import json
import re

from app.wire import ParseError, UnsupportedMediaType, ValidationFailed

JSON_MEDIA_TYPES = ('application/json',)
FORM_MEDIA_TYPES = ('application/x-www-form-urlencoded', 'multipart/form-data')

REQUIRED_MESSAGE = 'Bu alan zorunlu.'
NULL_MESSAGE = 'Bu alan boş bırakılmamalı.'
BLANK_MESSAGE = 'Bu alan boş bırakılmamalı.'
INTEGER_MESSAGE = 'Geçerli bir tam sayı giriniz.'
EMAIL_MESSAGE = 'Geçerli bir e-posta adresi girin.'
BOOLEAN_MESSAGE = 'Geçerli bir boolean bekleniyordu.'
NOT_A_DICT_MESSAGE = 'Geçersiz veri. Bir sözlük bekleniyor, ama var %s.'
_EMAIL = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


def media_type_of(request):
    header = request.headers.get('content-type', '')
    return header.split(';', 1)[0].strip().lower()


def unique_error(field, model):
    """The body a unique-constraint violation produces."""
    return {field: ['Bu %s alanına sahip %s zaten mevcut.' % (field, model)]}


async def parse_body(request, json_only=False):
    """Decode the body.

    An empty or undeclared document decodes to an empty mapping. A non-object JSON
    document is reported as a non-field error naming the type that arrived. Malformed
    JSON carries the decoder's own message. An undeclared body is read as a form, and a
    repeated form field collapses into a list. ``text/plain`` -- or a form body on a
    JSON-only route -- is 415.
    """
    media_type = media_type_of(request)
    raw = await request.body()
    if media_type in JSON_MEDIA_TYPES or (media_type == '' and raw[:1] in (b'{', b'[')):
        if not raw:
            return {}
        try:
            payload = json.loads(raw.decode('utf-8'))
        except ValueError as exc:
            raise ParseError('JSON parse error - %s' % exc)
        if payload is None:
            return {}
        if not isinstance(payload, dict):
            raise ValidationFailed({'non_field_errors': [
                NOT_A_DICT_MESSAGE % type(payload).__name__]})
        return payload
    if media_type in FORM_MEDIA_TYPES or media_type == '':
        if json_only and media_type in FORM_MEDIA_TYPES:
            raise UnsupportedMediaType(media_type)
        form = await request.form()
        data = {}
        for key in form.keys():
            values = form.getlist(key)
            data[key] = values[0] if len(values) == 1 else list(values)
        return data
    raise UnsupportedMediaType(media_type)


def is_form_request(request):
    return media_type_of(request) in FORM_MEDIA_TYPES


class Field:
    def __init__(self, name, required=True, allow_null=False, allow_blank=True,
                 kind='string', min_length=None, read_only=False, write_only=False,
                 default=None):
        self.name = name
        self.required = required
        self.allow_null = allow_null
        self.allow_blank = allow_blank
        self.kind = kind
        self.min_length = min_length
        self.read_only = read_only
        self.write_only = write_only
        self.default = default


def validate(payload, fields, partial=False):
    """Check ``payload`` against ``fields`` in DECLARED ORDER.

    Every offending field is reported in one pass, in the order the fields are declared,
    and an explicit ``null`` is checked before any type or format check, so a field that
    is not nullable is rejected before its value is ever coerced.
    """
    errors = {}
    data = {}
    for field in fields:
        if field.read_only:
            continue
        present = field.name in payload
        if not present:
            if field.required and not partial:
                errors[field.name] = [REQUIRED_MESSAGE]
            continue
        value = payload[field.name]
        if value is None:
            if field.allow_null:
                data[field.name] = None
            else:
                errors[field.name] = [NULL_MESSAGE]
            continue
        if field.kind == 'integer':
            try:
                value = int(value)
            except (TypeError, ValueError):
                errors[field.name] = [INTEGER_MESSAGE]
                continue
        elif field.kind == 'boolean':
            if isinstance(value, bool):
                pass
            elif str(value).lower() in ('true', '1'):
                value = True
            elif str(value).lower() in ('false', '0'):
                value = False
            else:
                errors[field.name] = [BOOLEAN_MESSAGE]
                continue
        elif field.kind == 'integer_list':
            if not isinstance(value, (list, tuple)):
                value = [value]
            coerced = []
            bad = False
            for item in value:
                try:
                    coerced.append(int(item))
                except (TypeError, ValueError):
                    errors[field.name] = [INTEGER_MESSAGE]
                    bad = True
                    break
            if bad:
                continue
            value = coerced
        elif field.kind == 'email':
            value = str(value)
            if not value:
                errors[field.name] = [BLANK_MESSAGE]
                continue
            if not _EMAIL.match(value):
                errors[field.name] = [EMAIL_MESSAGE]
                continue
        else:
            value = str(value)
            if not value and not field.allow_blank:
                errors[field.name] = [BLANK_MESSAGE]
                continue
        if field.min_length is not None and len(str(value)) < field.min_length:
            errors[field.name] = [
                'Bu alanın en az %d karakter barındırdığından emin olun.'
                % field.min_length]
            continue
        data[field.name] = value
    if errors:
        raise ValidationFailed(ordered_errors(errors, fields))
    return data


def ordered_errors(errors, fields):
    ordered = {}
    for field in fields:
        if field.name in errors:
            ordered[field.name] = errors[field.name]
    for key, value in errors.items():
        if key not in ordered:
            ordered[key] = value
    return ordered


def field_order(fields):
    return [field.name for field in fields]


def iter_errors(value):
    """Flatten a nested error structure to its leaf strings, in order."""
    if isinstance(value, dict):
        for item in value.values():
            yield from iter_errors(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from iter_errors(item)
    else:
        yield str(value)
