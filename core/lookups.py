"""Django-style keyword lookups on top of SQLAlchemy queries.

The view layer builds its filters as ``{'title__icontains': value}``
dictionaries
that are assembled by ``recipe.views.filter_param`` and only then handed to the
ORM.  Keeping that shape means the filter rules port across untouched, so this
module translates the keys instead of rewriting every view.
"""
from sqlalchemy import and_, or_
from sqlalchemy.orm import Query
from sqlalchemy.orm.relationships import RelationshipProperty

from core.exceptions import FieldError

LOOKUPS = (
    'exact',
    'iexact',
    'contains',
    'icontains',
    'in',
    'range',
    'gt',
    'gte',
    'lt',
    'lte',
    'isnull',
    'startswith',
    'istartswith',
    'endswith',
    'iendswith',
)


def is_model_instance(value):
    return hasattr(type(value), '__tablename__')


def as_id(value):
    if is_model_instance(value):
        return value.id
    return value


def as_ids(value):
    if isinstance(value, Query):
        value = value.all()
    return [as_id(item) for item in value]


def _relationship(attr):
    prop = getattr(attr, 'property', None)
    return prop if isinstance(prop, RelationshipProperty) else None


def _column_lookup(column, lookup, value):
    if lookup == 'exact':
        return column == as_id(value)
    if lookup == 'iexact':
        return column.ilike(value)
    if lookup == 'in':
        return column.in_(as_ids(value))
    if lookup == 'range':
        return column.between(value[0], value[1])
    if lookup == 'contains':
        return column.like('%{}%'.format(value))
    if lookup == 'icontains':
        return column.ilike('%{}%'.format(value))
    if lookup == 'startswith':
        return column.like('{}%'.format(value))
    if lookup == 'istartswith':
        return column.ilike('{}%'.format(value))
    if lookup == 'endswith':
        return column.like('%{}'.format(value))
    if lookup == 'iendswith':
        return column.ilike('%{}'.format(value))
    if lookup == 'gt':
        return column > as_id(value)
    if lookup == 'gte':
        return column >= as_id(value)
    if lookup == 'lt':
        return column < as_id(value)
    if lookup == 'lte':
        return column <= as_id(value)
    if lookup == 'isnull':
        return column.is_(None) if value else column.isnot(None)
    raise ValueError('Unsupported lookup: {}'.format(lookup))


def _attribute(model, name):
    attr = getattr(model, name, None)
    if attr is None:
        attr = getattr(model, '{}_id'.format(name))
    return attr


def _criterion(model, parts, lookup, value):
    attr = _attribute(model, parts[0])
    relationship = _relationship(attr)

    if len(parts) == 1:
        if relationship is None:
            return _column_lookup(attr, lookup, value)
        related = relationship.mapper.class_
        if lookup == 'exact':
            if value is not None and not isinstance(value, related):
                # Django resolves a related lookup through the target field, so
                # a non-model right-hand side ends up in ``int()``.
                raise TypeError(
                    "Field 'id' expected a number but got {!r}.".format(value)
                )
            if relationship.uselist:
                return attr == value
            # Compare the foreign key rather than the relationship: Django read
            # the primary key while building the query, so the filter keeps
            # working even if the instance leaves the session afterwards.
            local = relationship.local_remote_pairs[0][0]
            return local == as_id(value)
        return _column_lookup(related.id, lookup, value)

    if relationship is None:
        raise ValueError('Cannot traverse {}.{}'.format(model, parts[0]))

    related = relationship.mapper.class_
    inner = _criterion(related, parts[1:], lookup, value)
    return attr.any(inner) if relationship.uselist else attr.has(inner)


def criterion(model, key, value):
    """Turn one ``field__lookup=value`` pair into a SQLAlchemy expression."""
    parts = key.split('__')
    lookup = 'exact'
    if len(parts) > 1 and parts[-1] in LOOKUPS:
        lookup = parts.pop()
    return _criterion(model, parts, lookup, value)


def apply(query, model, kwargs):
    for key, value in kwargs.items():
        query = query.filter(criterion(model, key, value))
    return query


def column(model, name):
    """Resolve a column named at runtime, the way an ORM aggregate would.

    Aggregates name their column with a string, so a typo is only caught when
    the query is built.  Raising here keeps that timing.
    """
    attr = getattr(model, name, None)
    if attr is None:
        choices = ', '.join(sorted(c.key for c in model.__table__.columns))
        raise FieldError(
            "Cannot resolve keyword '{}' into field. "
            'Choices are: {}'.format(name, choices)
        )
    return attr


class Q:
    """``Q(user=user) | Q(sender=user)`` — an OR-able bag of lookups.

    Like Django's, it is resolved lazily: the model is not known until the
    queryset applies it, which is why the tree is kept as raw key/value pairs
    and only turned into SQLAlchemy expressions in ``resolve``.
    """

    AND = 'AND'
    OR = 'OR'

    def __init__(self, **kwargs):
        self.connector = self.AND
        self.children = list(kwargs.items())

    def _combine(self, other, connector):
        combined = Q()
        combined.connector = connector
        combined.children = [self, other]
        return combined

    def __or__(self, other):
        return self._combine(other, self.OR)

    def __and__(self, other):
        return self._combine(other, self.AND)

    def resolve(self, model):
        clauses = []
        for child in self.children:
            if isinstance(child, Q):
                clauses.append(child.resolve(model))
            else:
                key, value = child
                clauses.append(criterion(model, key, value))
        combine = or_ if self.connector == self.OR else and_
        return combine(*clauses)
