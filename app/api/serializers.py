"""Base schema plumbing shared by every serializer in the project.

The serializers are marshmallow schemas.  On top of the plain schema they carry
the request that triggered them (several validation rules in this project
depend on who is calling) and the ``instance``/``save()`` pair the views use to
turn a validated payload into a row.
"""

from collections.abc import Mapping

from marshmallow import EXCLUDE, Schema, missing, post_load, pre_load
from marshmallow import ValidationError as MarshmallowValidationError

from app.api import messages
from app.api.exceptions import ValidationError


class Serializer(Schema):

    class Meta:
        unknown = EXCLUDE
        ordered = True

    def __init__(self, instance=None, data=missing, context=None,
                 partial=False, many=False, **kwargs):
        super().__init__(many=many, partial=partial, **kwargs)
        self.instance = instance
        self.initial_data = data
        self.context = dict(context or {})
        self._validated_data = None

    @property
    def request(self):
        return self.context.get('request')

    @pre_load
    def _apply_to_internal_value(self, data, **kwargs):
        return self.to_internal_value(self._flatten(data))

    def _flatten(self, data):
        """Collapse a multi-valued form payload into plain Python values.

        Form data arrives as a multi-dict where one key can carry several
        values.  A list field has to read all of them and a single-valued
        field only one, and nothing in the payload itself says which is
        which, so the declared fields are what decides.

        A field that carries ``default_empty_html`` also gets that value when
        the payload omits it, because a form cannot express every absence as
        "leave this alone".
        """
        getlist = getattr(data, 'getlist', None)
        if getlist is None:
            return data
        flattened = {}
        for key in data.keys():
            field = self.fields.get(key)
            if getattr(field, 'many', False):
                flattened[key] = getlist(key)
            else:
                flattened[key] = data.get(key)
        if self.partial:
            return flattened
        for name, field in self.fields.items():
            empty_html = getattr(field, 'default_empty_html', None)
            if empty_html is None or field.dump_only or name in flattened:
                continue
            flattened[name] = empty_html
        return flattened

    def to_internal_value(self, data):
        """Reshape the raw payload before the fields look at it."""
        return data

    @post_load
    def _apply_validate(self, data, **kwargs):
        return self.validate(data)

    def validate(self, data):
        """Cross-field validation, run once every field has been accepted."""
        return data

    def is_valid(self, raise_exception=False):
        data = self.initial_data if self.initial_data is not missing else {}
        if not isinstance(data, Mapping):
            # The previous serializers refused anything but an object before
            # looking at a single field, naming the type they were handed.
            self._validated_data = None
            self._errors = {'non_field_errors': [
                messages.localize(messages.INVALID_DATA).format(
                    datatype=type(data).__name__)]}
            if raise_exception:
                raise ValidationError(self._errors)
            return False
        try:
            self._validated_data = self.load(data, partial=self.partial)
        except MarshmallowValidationError as exc:
            self._validated_data = None
            self._errors = normalize_errors(exc.messages)
            if raise_exception:
                raise ValidationError(self._errors)
            return False
        self._errors = {}
        return True

    @property
    def errors(self):
        return getattr(self, '_errors', {})

    @property
    def validated_data(self):
        if self._validated_data is None:
            raise AssertionError(
                'You must call `.is_valid()` before accessing '
                '`.validated_data`.'
            )
        return self._validated_data

    @property
    def data(self):
        if self.instance is not None:
            return self.dump(self.instance)
        return self.dump(self.validated_data)

    def save(self, **kwargs):
        validated_data = dict(self.validated_data, **kwargs)
        if self.instance is not None:
            self.instance = self.update(self.instance, validated_data)
        else:
            self.instance = self.create(validated_data)
        return self.instance

    def create(self, validated_data):
        raise NotImplementedError('`create()` must be implemented.')

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        return instance.save()


def run_validation(schema, data, partial=False):
    try:
        return schema.load(data, partial=partial)
    except MarshmallowValidationError as exc:
        raise ValidationError(normalize_errors(exc.messages))


def normalize_errors(messages):
    if isinstance(messages, dict):
        return {
            key: normalize_errors(value)
            for key, value in messages.items()
        }
    if isinstance(messages, list):
        return [
            item if isinstance(item, str) else normalize_errors(item)
            for item in messages
        ]
    return messages
