"""Marshmallow fields tuned to the wire format this API has always spoken.

Marshmallow ships English error messages and renders datetimes with a numeric
UTC offset.  Both are observable, so they are overridden here to keep the
responses byte-for-byte compatible with the pre-migration service.
"""

from marshmallow import ValidationError as MarshmallowValidationError
from marshmallow import fields, validate

from app.api import messages
from core.exceptions import ImproperlyConfigured

validate_email = validate.Email()


class _MessagesMixin:
    """Replace the framework defaults with the project's catalogue.

    marshmallow formats the stored message itself, which would freeze it in
    one language, so the entry is localized for the current request first.
    """

    default_error_messages = {
        'required': messages.REQUIRED,
        'null': messages.NULL,
        'validator_failed': messages.INVALID_INPUT,
    }

    def make_error(self, key, **kwargs):
        if key not in self.error_messages:
            return super().make_error(key, **kwargs)
        message = messages.localize(self.error_messages[key])
        return MarshmallowValidationError(
            message.format(**kwargs) if kwargs else message
        )


class CharField(_MessagesMixin, fields.String):
    """A text field with the blank/length semantics of the original API."""

    metadata_type = 'string'

    default_error_messages = {
        'invalid': messages.INVALID_STRING,
        'invalid_utf8': messages.INVALID_STRING,
    }

    def __init__(self, *, allow_blank=False, trim_whitespace=True,
                 min_length=None, max_length=None, **kwargs):
        self.allow_blank = allow_blank
        self.trim_whitespace = trim_whitespace
        self.min_length = min_length
        self.max_length = max_length
        super().__init__(**kwargs)

    def _deserialize(self, value, attr, data, **kwargs):
        value = super()._deserialize(value, attr, data, **kwargs)
        if self.trim_whitespace:
            value = value.strip()
        if value == '' and not self.allow_blank:
            raise MarshmallowValidationError(messages.localize(messages.BLANK))
        if self.min_length is not None and len(value) < self.min_length:
            raise MarshmallowValidationError(
                messages.localize(messages.MIN_LENGTH).format(
                    min_length=self.min_length)
            )
        if self.max_length is not None and len(value) > self.max_length:
            raise MarshmallowValidationError(
                messages.localize(messages.MAX_LENGTH).format(
                    max_length=self.max_length)
            )
        return value


class EmailField(CharField):
    """``CharField`` that additionally checks the address shape."""

    metadata_type = 'email'

    def _deserialize(self, value, attr, data, **kwargs):
        value = super()._deserialize(value, attr, data, **kwargs)
        try:
            validate_email(value)
        except MarshmallowValidationError:
            raise MarshmallowValidationError(
                messages.localize(messages.INVALID_EMAIL))
        return value


class SlugField(CharField):
    """A slug column; described as such on ``OPTIONS``."""

    metadata_type = 'slug'


class BooleanField(_MessagesMixin, fields.Boolean):
    metadata_type = 'boolean'
    default_error_messages = {'invalid': messages.INVALID_BOOLEAN}
    # A cleared checkbox is left out of a form submission entirely, so an
    # absent boolean means false there rather than "use the column default".
    default_empty_html = False


class IntegerField(_MessagesMixin, fields.Integer):
    metadata_type = 'integer'
    default_error_messages = {
        'invalid': messages.INVALID_INTEGER,
        'too_large': messages.INVALID_INTEGER,
    }


class DateTimeField(_MessagesMixin, fields.DateTime):
    """Serialize like the original API did: ISO-8601 with a ``Z`` suffix."""

    metadata_type = 'datetime'

    default_error_messages = {
        'invalid': messages.INVALID_DATETIME.format(format='iso-8601'),
        'invalid_awareness': messages.INVALID_DATETIME.format(
            format='iso-8601'
        ),
        'format': messages.INVALID_DATETIME.format(format='iso-8601'),
    }

    def _serialize(self, value, attr, obj, **kwargs):
        if value is None:
            return None
        rendered = value.isoformat()
        if rendered.endswith('+00:00'):
            rendered = rendered[:-6] + 'Z'
        elif value.tzinfo is None:
            # The columns hold naive UTC, which the original API rendered with
            # a ``Z`` suffix because ``USE_TZ`` made the values aware on read.
            rendered += 'Z'
        return rendered


class PrimaryKeyRelatedField(_MessagesMixin, fields.Field):
    """Represent a relation by the primary key of the related row."""

    default_error_messages = {
        'does_not_exist': messages.DOES_NOT_EXIST,
        'incorrect_type': messages.INCORRECT_TYPE,
    }

    def __init__(self, model, *, many=False, **kwargs):
        self.model = model
        self.many = many
        super().__init__(**kwargs)

    def _serialize(self, value, attr, obj, **kwargs):
        if value is None:
            return None
        if self.many:
            return [item.id for item in value]
        return value.id if hasattr(value, 'id') else value

    def _load_one(self, value):
        from app.extensions import db
        try:
            pk = int(value)
        except (TypeError, ValueError):
            raise MarshmallowValidationError(
                messages.localize(messages.INCORRECT_TYPE).format(
                    data_type=type(value).__name__
                )
            )
        instance = db.session.get(self.model, pk)
        if instance is None:
            raise MarshmallowValidationError(
                messages.localize(messages.DOES_NOT_EXIST).format(pk_value=pk)
            )
        return instance

    def _deserialize(self, value, attr, data, **kwargs):
        if self.many:
            if not isinstance(value, (list, tuple)):
                value = [value]
            return [self._load_one(item) for item in value]
        return self._load_one(value)


class ReadOnlyField(fields.Field):
    """Dump whatever the attribute holds, never accept it on input."""

    def __init__(self, **kwargs):
        kwargs.setdefault('dump_only', True)
        super().__init__(**kwargs)

    def _serialize(self, value, attr, obj, **kwargs):
        return value


class ImageField(fields.Field):
    """Render a stored upload as the path the original API returned."""

    metadata_type = 'image upload'
    #: The column the upload's name is stored in.
    max_length = 100

    def _serialize(self, value, attr, obj, **kwargs):
        return value or None

    def _deserialize(self, value, attr, data, **kwargs):
        return value


class NestedField(fields.Field):
    """Embed another serializer, sharing the outer serializer's context."""

    def __init__(self, schema_class, *, many=False, **kwargs):
        self.schema_class = schema_class
        self.many = many
        kwargs.setdefault('dump_only', True)
        super().__init__(**kwargs)

    def _serialize(self, value, attr, obj, **kwargs):
        if value is None:
            return None
        context = getattr(self.parent, 'context', None)
        schema = self.schema_class(context=context)
        if self.many:
            return [schema.dump(item) for item in value]
        return schema.dump(value)


class SerializerMethodField(fields.Field):
    """Take the value from ``get_<field name>()`` on the serializer."""

    def __init__(self, method_name=None, **kwargs):
        self.method_name = method_name
        kwargs.setdefault('dump_only', True)
        super().__init__(**kwargs)

    def _bind_to_schema(self, field_name, schema):
        if self.method_name is None:
            self.method_name = 'get_{}'.format(field_name)
        super()._bind_to_schema(field_name, schema)

    def serialize(self, attr, obj, accessor=None, **kwargs):
        return getattr(self.parent, self.method_name)(obj)


class UnknownModelField(fields.Field):
    """A serializer field naming something the model does not have.

    Listing a field that no model column backs is a configuration error, and
    the previous framework refused to build the serializer at all rather than
    quietly emitting a null.  The failure only ever surfaced once a record was
    actually read or written, so it is raised from the (de)serialization hooks
    instead of at import time.
    """

    def __init__(self, model, **kwargs):
        self.model = model
        super().__init__(**kwargs)

    def _fail(self):
        raise ImproperlyConfigured(
            'Field name `{}` is not valid for model `{}`.'.format(
                self.name, self.model.__name__
            )
        )

    def _serialize(self, value, attr, obj, **kwargs):
        self._fail()

    def _deserialize(self, value, attr, data, **kwargs):
        self._fail()

    def serialize(self, attr, obj, accessor=None, **kwargs):
        self._fail()
