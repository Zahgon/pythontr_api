from app.extensions import db

from .base import SaveMixin, now
from .model_content_type import ContentType


class Comment(db.Model, SaveMixin):
    __tablename__ = 'core_comment'
    __app_label__ = 'core'

    id = db.Column(db.BigInteger().with_variant(db.Integer, 'sqlite'),
                   primary_key=True)
    # 32 bit on purpose: django_content_type was owned by a contrib app that
    # never moved off AutoField, so the column it points at stayed an int4.
    content_type_id = db.Column(
        db.Integer,
        db.ForeignKey('django_content_type.id', ondelete='CASCADE'),
        nullable=False,
    )
    object_id = db.Column(db.Integer, nullable=False)

    created_at = db.Column(db.DateTime, nullable=False, default=now)
    content = db.Column(db.Text, nullable=False, default='')
    email = db.Column(db.String(100), nullable=False, default='')
    name = db.Column(db.String(50), nullable=False, default='')
    ip = db.Column(db.String(100), nullable=False, default='')
    user_id = db.Column(
        db.BigInteger().with_variant(db.Integer, 'sqlite'),
        db.ForeignKey('core_user.id', ondelete='SET NULL'),
        nullable=True,
    )
    is_active = db.Column(db.Boolean, nullable=False, default=False)
    is_delete = db.Column(db.Boolean, nullable=False, default=False)

    content_type = db.relationship('ContentType')
    user = db.relationship('User')

    def __init__(self, **kwargs):
        kwargs.setdefault('content', '')
        super().__init__(**kwargs)

    @property
    def pk(self):
        return self.id

    @property
    def content_object(self):
        """``GenericForeignKey('content_type', 'object_id')``."""
        content_type = self.content_type
        if content_type is None:
            content_type = db.session.get(ContentType, self.content_type_id)
        if content_type is None:
            return None
        model = content_type.model_class()
        if model is None:
            return None
        return db.session.get(model, self.object_id)

    @content_object.setter
    def content_object(self, value):
        if value is None:
            self.content_type_id = None
            self.object_id = None
            return
        self.content_type = ContentType.get_for_model(type(value))
        self.object_id = value.pk

    @property
    def comments(self):
        """``GenericRelation('self')``: replies pointing back at this row."""
        return Comment.query.filter_by(
            content_type_id=ContentType.get_for_model(Comment).id,
            object_id=self.id,
        )

    def save(self, *args, **kwargs):
        if self.created_at is None:
            self.created_at = now()
        return super(Comment, self).save()

    def __str__(self):
        return self.content
