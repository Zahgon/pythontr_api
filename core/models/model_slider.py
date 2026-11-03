from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.text import slugify

from .model_user import utcnow


def slider_image_file_path(instance, filename):
    from app import settings
    f_name, ext = filename.split('.')
    allowed_chars = \
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._"
    sanitized_filename = ''.join(c for c in f_name if c in allowed_chars)
    slug = slugify(sanitized_filename)
    file_path = f'{settings.IMAGE_ROOT}/{slug}.{ext}'
    return file_path


class Slider(Base):
    __tablename__ = 'core_slider'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    title: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    link: Mapped[str] = mapped_column(String(255), nullable=True)
    image: Mapped[str] = mapped_column(String(100), nullable=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('core_user.id'), nullable=True)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=False)
    is_approval: Mapped[bool] = mapped_column(nullable=False, default=False)
    approval_user_id: Mapped[int] = mapped_column(ForeignKey('core_user.id'), nullable=True)
    is_delete: Mapped[bool] = mapped_column(nullable=False, default=False)

    user = relationship('User', foreign_keys=[user_id], lazy='joined')
    approval_user = relationship('User', foreign_keys=[approval_user_id], lazy='joined')

    @property
    def pk(self):
        return self.id

    def __str__(self):
        return self.title

    @property
    def image_url(self):
        from app import settings
        image_url = None
        if self.image:
            image_url = ('/%s' % self.image).replace(settings.APLICATION_NAME, '')
        return image_url
