from app.extensions import db

from .base import Manager, SaveMixin, classproperty, now


class MessageManager(Manager):
    """The default manager hides soft-deleted rows.

    Every read in the project goes through ``Message.objects``, so the
    ``is_delete=False`` filter has to be baked into the manager rather than
    applied at the call sites — that is what makes a deleted message vanish
    from the inbox without any view changing.
    """

    def get_queryset(self):
        return self.model.query.filter(self.model.is_delete.is_(False))


class Message(db.Model, SaveMixin):
    __tablename__ = 'core_message'
    __app_label__ = 'core'

    id = db.Column(db.BigInteger().with_variant(db.Integer, 'sqlite'),
                   primary_key=True)
    created_at = db.Column(db.DateTime, nullable=False, default=now)
    sender_id = db.Column(
        db.BigInteger().with_variant(db.Integer, 'sqlite'),
        db.ForeignKey('core_user.id', ondelete='SET NULL'),
        nullable=True,
    )
    user_id = db.Column(
        db.BigInteger().with_variant(db.Integer, 'sqlite'),
        db.ForeignKey('core_user.id', ondelete='SET NULL'),
        nullable=True,
    )

    subject = db.Column(db.String(255), nullable=False, default='')
    content = db.Column(db.Text, nullable=False, default='')
    ip = db.Column(db.String(100), nullable=False, default='')

    is_read = db.Column(db.Boolean, nullable=False, default=False)
    is_delete = db.Column(db.Boolean, nullable=False, default=False)
    is_sender_delete = db.Column(db.Boolean, nullable=False, default=False)

    sender = db.relationship('User', foreign_keys=[sender_id],
                             backref='sender_user')
    user = db.relationship('User', foreign_keys=[user_id],
                           backref='reciever_user')

    @classproperty
    def all_objects(cls):
        """The unfiltered queryset, i.e. Django's ``_base_manager``."""
        return cls.query

    @property
    def pk(self):
        return self.id

    def save(self, *args, **kwargs):
        if self.created_at is None:
            self.created_at = now()
        return super(Message, self).save()

    def __str__(self):
        return self.subject


Message.objects = MessageManager(Message)
