"""Port of ``django.contrib.contenttypes``.

``Comment`` is a generic-relation table: it stores a ``content_type_id`` /
``object_id`` pair and the API exposes the numeric content-type id directly, so
the table has to keep existing with the same rows and the same ids.  Only the
two columns the project actually reads (``app_label``, ``model``) are kept.
"""
from app.extensions import db

from .base import Manager, SaveMixin


class ContentTypeManager(Manager):

    def get_for_model(self, model):
        return self.model.get_for_model(model)

    def get_for_id(self, pk):
        return self.model.get_for_id(pk)


class ContentType(db.Model, SaveMixin):
    __tablename__ = 'django_content_type'
    __table_args__ = (
        db.UniqueConstraint(
            'app_label',
            'model',
            name='django_content_type_app_label_model_uniq',
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    app_label = db.Column(db.String(100), nullable=False)
    model = db.Column(db.String(100), nullable=False)

    @classmethod
    def get_for_model(cls, model):
        """``ContentType.objects.get_for_model`` without the local cache.

        Django's manager is a ``get_or_create``: the contenttypes app seeds the
        table in ``post_migrate``, but a model it has never seen is inserted on
        first use.  Keeping the create-on-miss branch is what lets a fresh
        database hand out the same ids the seeded one did.
        """
        app_label = model.__app_label__
        name = model.__name__.lower()
        content_type = cls.query.filter_by(
            app_label=app_label, model=name
        ).one_or_none()
        if content_type is None:
            content_type = cls(app_label=app_label, model=name).save()
        return content_type

    @classmethod
    def get_for_id(cls, pk):
        return db.session.get(cls, pk)

    def model_class(self):
        from core import models

        for candidate in models.CONTENT_TYPE_MODELS:
            if (
                candidate.__app_label__ == self.app_label
                and candidate.__name__.lower() == self.model
            ):
                return candidate
        return None

    def __str__(self):
        return self.model


ContentType.objects = ContentTypeManager(ContentType)
