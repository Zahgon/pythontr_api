from flask import current_app

from app.extensions import db
from core import storage
from core.text import slugify

from .base import SaveMixin, now


def slider_image_file_path(instance, filename):
    f_name, ext = filename.split('.')
    allowed_chars = \
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._"
    sanitized_filename = ''.join(c for c in f_name if c in allowed_chars)
    slug = slugify(sanitized_filename)
    file_path = f'{current_app.config["IMAGE_ROOT"]}/{slug}.{ext}'
    return file_path


class Slider(db.Model, SaveMixin):
    __tablename__ = 'core_slider'
    __app_label__ = 'core'

    id = db.Column(db.BigInteger().with_variant(db.Integer, 'sqlite'),
                   primary_key=True)
    created_at = db.Column(db.DateTime, nullable=False, default=now)
    updated_at = db.Column(db.DateTime, nullable=False, default=now)
    title = db.Column(db.String(255), nullable=False, unique=True,
                      default='')
    description = db.Column(db.Text, nullable=True)
    link = db.Column(db.String(255), nullable=True)
    image = db.Column(db.String(100), nullable=True)
    user_id = db.Column(
        db.BigInteger().with_variant(db.Integer, 'sqlite'),
        db.ForeignKey('core_user.id', ondelete='SET NULL'),
        nullable=True,
    )
    is_active = db.Column(db.Boolean, nullable=False, default=False)
    is_approval = db.Column(db.Boolean, nullable=False, default=False)
    approval_user_id = db.Column(
        db.BigInteger().with_variant(db.Integer, 'sqlite'),
        db.ForeignKey('core_user.id', ondelete='SET NULL'),
        nullable=True,
    )
    is_delete = db.Column(db.Boolean, nullable=False, default=False)

    user = db.relationship('User', foreign_keys=[user_id])
    approval_user = db.relationship('User', foreign_keys=[approval_user_id],
                                    backref='approved_sliders')

    @property
    def pk(self):
        return self.id

    def save(self, *args, **kwargs):
        stamp = now()
        if self.created_at is None:
            self.created_at = stamp
        if self.updated_at is None:
            self.updated_at = stamp
        self.image = storage.persist(self, self.image, slider_image_file_path)
        return super(Slider, self).save()

    def __str__(self):
        return self.title

    @property
    def image_url(self):
        image_url = None
        if self.image:
            image_url = self.image.replace(
                current_app.config['APLICATION_NAME'], ''
            )
        return image_url
