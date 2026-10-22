"""The metadata an ``OPTIONS`` request answers with.

The previous framework described every view on ``OPTIONS``: its name and
description, the media types it renders and parses, and -- for the writes the
caller may make -- an ``actions`` map describing each serializer field the way
its ``SimpleMetadata`` did.  Clients build their forms from that map, so the
field descriptions are reproduced here from the serializer fields.
"""
from sqlalchemy.orm.exc import NoResultFound

from app.api import fields as api_fields
from app.api import messages
from app.api.exceptions import APIException

#: The labels that do not follow from the field name.
LABELS = {'id': 'ID'}

#: Field attributes reported when the field has them, in this order.
ATTRIBUTES = ('min_length', 'max_length')


def default_label(name):
    if name in LABELS:
        return LABELS[name]
    text = name.replace('_', ' ')
    return text[:1].upper() + text[1:]


def field_info(name, field):
    info = {
        'type': getattr(field, 'metadata_type', 'field'),
        'required': bool(field.required),
        'read_only': bool(field.dump_only),
    }
    label = field.metadata.get('label')
    info['label'] = messages.localize(label) if label else default_label(name)
    for attribute in ATTRIBUTES:
        value = getattr(field, attribute, None)
        if value is None:
            value = field.metadata.get(attribute)
        if value is not None:
            info[attribute] = value
    if isinstance(field, api_fields.NestedField) and field.many:
        info['child'] = {
            'type': 'nested object',
            'required': False,
            'read_only': True,
            'children': serializer_info(field.schema_class()),
        }
    return info


def serializer_info(serializer):
    return {name: field_info(name, field)
            for name, field in serializer.fields.items()}


class _MethodOverride:
    """The request as the permission checks would see it for ``method``."""

    def __init__(self, request, method):
        self._request = request
        self.method = method

    def __getattr__(self, name):
        return getattr(self._request, name)


def determine_actions(request, view):
    """``{"PUT" | "POST": field map}`` for the writes the caller may make."""
    actions = {}
    if not hasattr(view, 'get_serializer'):
        return actions
    for method in ('PUT', 'POST'):
        if method not in view.allowed_methods:
            continue
        original = view.request
        view.request = _MethodOverride(request, method)
        try:
            view.check_permissions(view.request)
            if method == 'PUT' and hasattr(view, 'get_object'):
                view.get_object()
        except (APIException, NoResultFound):
            continue
        else:
            actions[method] = serializer_info(view.get_serializer())
        finally:
            view.request = original
    return actions
