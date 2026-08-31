"""Shared model plumbing.

Django gave every model a ``save()`` that ran field-level bookkeeping (slug
generation, ``auto_now`` stamps) before hitting the database.  The SQLAlchemy
models keep that shape: each one owns an explicit ``save()`` so the call sites
in the views and serializers read the same as before.
"""
from datetime import datetime

from app.extensions import db


def now():
    """Naive UTC, matching what Django wrote to the column with ``USE_TZ``."""
    return datetime.utcnow()


class classproperty:
    """``property`` for classmethods, used for the model managers."""

    def __init__(self, method):
        self.method = method

    def __get__(self, instance, owner=None):
        return self.method(owner)


class QuerySet:
    """A SQLAlchemy ``Query`` wearing the two Django habits the callers keep.

    Everything unknown is delegated straight to the wrapped query, so the
    SQLAlchemy API stays available.  Only two things are translated: ``Q``
    objects and string field names in ``order_by`` (``'id'``, ``'-id'``), which
    SQLAlchemy does not accept.  ``last()`` is provided because Django's
    querysets have it and the message tests read through it.
    """

    def __init__(self, model, query):
        self.model = model
        self.query = query

    def __getattr__(self, name):
        return getattr(self.query, name)

    def __iter__(self):
        return iter(self.query)

    def __getitem__(self, item):
        return self.query[item]

    def filter(self, *args, **kwargs):
        from core import lookups

        criteria = [
            arg.resolve(self.model) if isinstance(arg, lookups.Q) else arg
            for arg in args
        ]
        query = self.query.filter(*criteria) if criteria else self.query
        return QuerySet(self.model, lookups.apply(query, self.model, kwargs))

    def order_by(self, *fields):
        from core import lookups

        columns = []
        for field in fields:
            if not isinstance(field, str):
                columns.append(field)
                continue
            descending = field.startswith('-')
            column = lookups.column(self.model, field.lstrip('-'))
            columns.append(column.desc() if descending else column)
        return QuerySet(self.model, self.query.order_by(*columns))

    def last(self):
        rows = self.query.all()
        return rows[-1] if rows else None

    def exists(self):
        # SQLAlchemy's ``Query.exists()`` builds an EXISTS clause; the callers
        # want the boolean answer their previous queryset gave them.
        return self.query.first() is not None


class Manager:
    """The subset of ``Model.objects`` the project actually calls.

    Django handed every model a default manager; the call sites here only ever
    use ``create``/``filter``/``get``/``all``, so those are what is provided.
    ``create()`` goes through the model's own ``save()`` so the slug and
    ``updated_at`` bookkeeping still runs, exactly as Django's did.
    ``get_queryset()`` is the hook a model overrides to bake a filter into the
    manager, the way ``MessageManager`` hides soft-deleted rows.
    """

    def __init__(self, model):
        self.model = model

    def get_queryset(self):
        return self.model.query

    def create(self, **kwargs):
        return self.model(**kwargs).save()

    def filter(self, *args, **kwargs):
        queryset = QuerySet(self.model, self.get_queryset())
        return queryset.filter(*args, **kwargs)

    def get(self, **kwargs):
        return self.filter(**kwargs).one()

    def all(self):
        return QuerySet(self.model, self.get_queryset())


class SaveMixin:

    @classproperty
    def objects(cls):
        return Manager(cls)

    def save(self):
        db.session.add(self)
        db.session.commit()
        return self

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    def refresh_from_db(self):
        db.session.refresh(self)
        return self

    @classmethod
    def get(cls, pk):
        return db.session.get(cls, pk)


def unique_slug(model, column, value):
    """Django's ``get_slug`` loop: append ``-1``, ``-2`` … until free.

    The row being saved is *not* excluded from the uniqueness probe, exactly
    as in the original.  Because the slug is recomputed on every ``save()``,
    saving a record twice drifts its slug to ``name-1``.  That quirk is
    observable through the API, so it is preserved rather than fixed.
    """
    from core.text import slugify

    slug = slugify(str(value).replace('ı', 'i'))
    unique = slug
    number = 1
    with db.session.no_autoflush:
        while (
            db.session.query(model)
            .filter(column == unique)
            .first() is not None
        ):
            unique = '{}-{}'.format(slug, number)
            number += 1
    return unique
