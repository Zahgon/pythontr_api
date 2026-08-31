"""``values()`` / ``annotate()`` style aggregation over SQLAlchemy queries.

The reporting endpoints in ``user/admin`` were written against Django's
``QuerySet.values(...).annotate(...)`` chain and return the resulting rows
verbatim as JSON. Reproducing that chain here keeps those views - and the JSON
they emit - unchanged; the alternative would have been to rewrite every
report as
a hand-rolled ``select()``, which changes the row shape and the key order.
"""
from sqlalchemy import Integer, cast, distinct as sa_distinct, extract, func

from app.extensions import db
from core import lookups


class Aggregate(object):
    """Base for ``Count`` / ``Avg``: an aggregate over one model column."""

    function = None

    def __init__(self, field, distinct=False):
        self.field = field
        self.distinct = distinct

    def expression(self, model):
        column = lookups.column(model, self.field)
        if self.distinct:
            column = sa_distinct(column)
        return self.function(column)


class Count(Aggregate):
    function = staticmethod(func.count)


class Avg(Aggregate):
    function = staticmethod(func.avg)


class ExtractHour(object):
    """Hour of a timestamp column, as an integer."""

    def __init__(self, field):
        self.field = field

    def expression(self, model):
        column = lookups.column(model, self.field)
        # SQLite has no EXTRACT; Django registers its own helper there and
        # returns an integer either way, so the cast keeps the JSON identical
        # across both backends.
        if db.engine.dialect.name == 'sqlite':
            return cast(func.strftime('%H', column), Integer)
        return extract('hour', column)


class ValuesQuery(object):
    """The tail of a ``values().annotate().order_by()[:n]`` chain."""

    def __init__(self, query, model, values=(), extra=None, aggregates=None,
                 order=(), limit=None, offset=None):
        self.query = query
        self.model = model
        self.values_fields = tuple(values)
        self.extra = dict(extra or {})
        self.aggregates = dict(aggregates or {})
        self.order = tuple(order)
        self.limit = limit
        self.offset = offset

    def _clone(self, **kwargs):
        state = {
            'values': self.values_fields,
            'extra': self.extra,
            'aggregates': self.aggregates,
            'order': self.order,
            'limit': self.limit,
            'offset': self.offset,
        }
        state.update(kwargs)
        return ValuesQuery(self.query, self.model, **state)

    def values(self, *fields):
        return self._clone(values=self.values_fields + fields)

    def annotate(self, **kwargs):
        extra = dict(self.extra)
        aggregates = dict(self.aggregates)
        for name, value in kwargs.items():
            if isinstance(value, Aggregate):
                aggregates[name] = value
            else:
                extra[name] = value
        return self._clone(extra=extra, aggregates=aggregates)

    def order_by(self, *fields):
        return self._clone(order=fields)

    def count(self):
        return self.query.count()

    def _columns(self):
        """Return ``(grouped, labelled)``: GROUP BY set and columns."""
        grouped = []
        labelled = {}
        for name in self.values_fields:
            if name in self.extra:
                expression = self.extra[name].expression(self.model)
            else:
                expression = lookups.column(self.model, name)
            grouped.append(expression)
            labelled[name] = expression.label(name)
        for name, aggregate in self.aggregates.items():
            labelled[name] = aggregate.expression(self.model).label(name)
        return grouped, labelled

    def _statement(self):
        grouped, labelled = self._columns()
        names = list(self.values_fields) + list(self.aggregates)
        query = self.query.with_entities(*[labelled[name] for name in names])
        if grouped:
            query = query.group_by(*grouped)
        for field in self.order:
            descending = field.startswith('-')
            name = field[1:] if descending else field
            expression = labelled[name]
            query = query.order_by(
                expression.desc() if descending else expression.asc()
            )
        if self.offset:
            query = query.offset(self.offset)
        if self.limit is not None:
            query = query.limit(self.limit)
        return names, query

    def __iter__(self):
        names, query = self._statement()
        for row in query.all():
            yield dict(zip(names, row))

    def __getitem__(self, item):
        if isinstance(item, slice):
            offset = item.start or 0
            limit = None if item.stop is None else item.stop - offset
            return self._clone(limit=limit, offset=offset or None)
        return list(self)[item]


def queryset(query, model):
    """Wrap a query so ``values()``/``annotate()`` can be chained."""
    return ValuesQuery(query, model)
