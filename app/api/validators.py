"""Validators that need to reach the database.

Uniqueness used to be derived automatically from the model definition, and the
message it produced named both the field and the model.  Those messages are
part of the API's responses, so they are spelled out at each call site instead
of being regenerated.
"""

from marshmallow import ValidationError as MarshmallowValidationError

from app.api import messages


def unique_check(model, column, value, instance=None, field=None, label=None):
    """Raise unless ``value`` is free in ``column``.

    ``instance`` is the row being updated, if any; it is excluded from the
    check so that saving a row without changing the field is not an error.
    """
    query = model.query.filter(column == value)
    instance_id = None
    if instance is not None:
        instance_id = getattr(instance, 'id', None)
    if instance_id is not None:
        query = query.filter(model.id != instance_id)
    if query.first() is not None:
        raise MarshmallowValidationError(
            messages.UNIQUE.format(
                field=field or column.key,
                model=label or model.__name__.lower(),
            )
        )
