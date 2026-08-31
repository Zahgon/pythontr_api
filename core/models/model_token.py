"""Port of ``rest_framework.authtoken``.

The project used DRF's token app for ``POST /api/user/token/`` and for the
``Authorization: Token <key>`` header.  The table keeps its original name and
shape so issued tokens survive the migration.
"""
import binascii
import os

from app.extensions import db

from .base import SaveMixin, now


class Token(db.Model, SaveMixin):
    __tablename__ = 'authtoken_token'

    key = db.Column(db.String(40), primary_key=True)
    user_id = db.Column(
        db.BigInteger().with_variant(db.Integer, 'sqlite'),
        db.ForeignKey('core_user.id', ondelete='CASCADE'),
        nullable=False,
        unique=True,
    )
    created = db.Column(db.DateTime, nullable=False, default=now)

    user = db.relationship('User', back_populates='auth_token')

    @staticmethod
    def generate_key():
        return binascii.hexlify(os.urandom(20)).decode()

    @classmethod
    def get_or_create(cls, user):
        """``get_or_create(user=user)`` -> ``(token, created)``."""
        token = cls.query.filter_by(user_id=user.id).first()
        if token is not None:
            return token, False
        token = cls(key=cls.generate_key(), user_id=user.id, created=now())
        db.session.add(token)
        db.session.commit()
        return token, True

    def __str__(self):
        return self.key
