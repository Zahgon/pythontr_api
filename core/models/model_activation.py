import uuid

from datetime import timedelta

from app.extensions import db

from .base import SaveMixin, now
from .model_user import User  # noqa: F401  (kept for import parity)


class ActivationCode(db.Model, SaveMixin):
    __tablename__ = 'core_activationcode'
    __app_label__ = 'core'

    id = db.Column(db.BigInteger().with_variant(db.Integer, 'sqlite'),
                   primary_key=True)
    user_id = db.Column(
        db.BigInteger().with_variant(db.Integer, 'sqlite'),
        db.ForeignKey('core_user.id', ondelete='CASCADE'),
        nullable=False,
    )
    code = db.Column(
        db.String(36), nullable=False, default=lambda: str(uuid.uuid4())
    )
    created_at = db.Column(db.DateTime, nullable=False, default=now)
    expires_at = db.Column(db.DateTime, nullable=False)
    is_used = db.Column(db.Boolean, nullable=False, default=False)

    user = db.relationship('User')

    @property
    def pk(self):
        return self.id

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = now() + timedelta(hours=24)
        if self.code is None:
            self.code = str(uuid.uuid4())
        if self.created_at is None:
            self.created_at = now()
        return super().save()

    @property
    def is_expired(self):
        return now() > self.expires_at

    @classmethod
    def create_activation_code(cls, user):
        cls.query.filter_by(user_id=user.id, is_used=False).update(
            {'is_used': True}
        )
        db.session.commit()
        return cls(user_id=user.id).save()
