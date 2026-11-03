from datetime import datetime

from sqlalchemy import (Column, DateTime, ForeignKey, Integer, String, Table,
                        Text, select)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.text import slugify

from .model_category import Category
from .model_user import utcnow

article_categories = Table(
    'core_article_categories', Base.metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('article_id', ForeignKey('core_article.id'), nullable=False),
    Column('category_id', ForeignKey('core_category.id'), nullable=False),
)


def article_image_file_path(instance, filename):
    from app import settings
    f_name, ext = filename.split('.')
    allowed_chars = \
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._"
    sanitized_filename = ''.join(
        c for c in f_name if c in allowed_chars).strip()
    slug = slugify(sanitized_filename)
    folder = instance.pk if instance.pk else 'temp'
    file_path = f'{settings.ARTICLE_ROOT}{folder}/{slug}.{ext}'
    return file_path


class Article(Base):
    __tablename__ = 'core_article'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    title: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    title_h1: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default='')
    content: Mapped[str] = mapped_column(Text, nullable=False, default='')
    image: Mapped[str] = mapped_column(String(100), nullable=True)
    read_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    slug: Mapped[str] = mapped_column(String(150), nullable=False, unique=True, default='')
    user_id: Mapped[int] = mapped_column(ForeignKey('core_user.id'), nullable=True)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=False)
    is_approval: Mapped[bool] = mapped_column(nullable=False, default=False)
    approval_user_id: Mapped[int] = mapped_column(ForeignKey('core_user.id'), nullable=True)
    is_delete: Mapped[bool] = mapped_column(nullable=False, default=False)

    user = relationship('User', foreign_keys=[user_id], lazy='joined')
    approval_user = relationship('User', foreign_keys=[approval_user_id], lazy='joined')
    categories: Mapped[list[Category]] = relationship(
        Category, secondary=article_categories, lazy='selectin',
        order_by='core_article_categories.c.id')

    @property
    def pk(self):
        return self.id

    def get_slug(self, session):
        """As with a user, the row being saved is not excluded from the search."""
        slug = slugify(self.title_h1.replace('ı', 'i'))
        unique = slug
        number = 1
        while session.scalar(select(Article.id).where(Article.slug == unique)) is not None:
            unique = '{}-{}'.format(slug, number)
            number += 1
        return unique

    def save(self, session):
        if not self.title_h1:
            self.title_h1 = self.title
        self.updated_at = utcnow()
        self.slug = self.get_slug(session)
        if self.created_at is None:
            self.created_at = self.updated_at
        session.add(self)
        session.flush()
        return self

    def __str__(self):
        return self.title

    @property
    def image_url(self):
        from app import settings
        image_url = None
        if self.image:
            image_url = ('/%s' % self.image).replace(settings.APLICATION_NAME, '')
        return image_url
