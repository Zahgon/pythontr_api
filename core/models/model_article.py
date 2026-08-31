import os
import shutil

from flask import current_app

from app.extensions import db
from core import storage
from core.text import slugify

from .base import SaveMixin, now, unique_slug
from .model_category import Category  # noqa: F401  (kept for import parity)
from .model_comment import Comment
from .model_content_type import ContentType


def article_image_file_path(instance, filename):
    f_name, ext = filename.split('.')
    allowed_chars = \
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._"
    sanitized_filename = ''.join(
        c for c in f_name if c in allowed_chars).strip()
    slug = slugify(sanitized_filename)
    folder = instance.pk if instance.pk else 'temp'
    file_path = f'{current_app.config["ARTICLE_ROOT"]}{folder}/{slug}.{ext}'
    return file_path


article_categories = db.Table(
    'core_article_categories',
    db.Column('id', db.BigInteger().with_variant(db.Integer, 'sqlite'),
              primary_key=True),
    db.Column('article_id',
              db.BigInteger().with_variant(db.Integer, 'sqlite'),
              db.ForeignKey('core_article.id', ondelete='CASCADE'),
              nullable=False),
    db.Column('category_id',
              db.BigInteger().with_variant(db.Integer, 'sqlite'),
              db.ForeignKey('core_category.id', ondelete='CASCADE'),
              nullable=False),
    db.UniqueConstraint(
        'article_id', 'category_id',
        name='core_article_categories_article_id_category_id_uniq',
    ),
)


class Article(db.Model, SaveMixin):
    __tablename__ = 'core_article'
    __app_label__ = 'core'

    id = db.Column(db.BigInteger().with_variant(db.Integer, 'sqlite'),
                   primary_key=True)
    created_at = db.Column(db.DateTime, nullable=False, default=now)
    updated_at = db.Column(db.DateTime, nullable=False, default=now)
    title = db.Column(db.String(255), nullable=False, unique=True,
                      default='')
    title_h1 = db.Column(db.String(255), nullable=False, default='')
    description = db.Column(db.Text, nullable=False, default='')
    content = db.Column(db.Text, nullable=False, default='')
    image = db.Column(db.String(100), nullable=True)
    read_count = db.Column(db.Integer, nullable=False, default=0)
    slug = db.Column(db.String(150), nullable=False, unique=True)
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

    categories = db.relationship(
        'Category', secondary=article_categories, backref='article',
        lazy='selectin',
    )
    user = db.relationship('User', foreign_keys=[user_id])
    approval_user = db.relationship('User', foreign_keys=[approval_user_id])

    def __init__(self, **kwargs):
        kwargs.setdefault('description', '')
        kwargs.setdefault('content', '')
        kwargs.setdefault('title_h1', '')
        super().__init__(**kwargs)

    @property
    def pk(self):
        return self.id

    @property
    def comments(self):
        """``GenericRelation(Comment)``."""
        return Comment.query.filter_by(
            content_type_id=ContentType.get_for_model(Article).id,
            object_id=self.id,
        )

    def get_slug(self):
        return unique_slug(Article, Article.slug, self.title_h1)

    def save(self, *args, **kwargs):
        if not self.title_h1:
            self.title_h1 = self.title

        self.updated_at = now()
        if self.created_at is None:
            self.created_at = self.updated_at
        self.slug = self.get_slug()
        self.image = storage.persist(self, self.image, article_image_file_path)

        super(Article, self).save()
        if self.image and 'temp' in self.image_path:
            filename = os.path.basename(self.image).strip()
            article_root = current_app.config['ARTICLE_ROOT']
            new_path = f'{article_root}{self.pk}/{filename}'
            os.makedirs(os.path.dirname(new_path), exist_ok=True)

            old_path = self.image_path
            self.image = new_path
            super(Article, self).save()

            if os.path.exists(old_path):
                shutil.move(old_path, new_path)

        return self

    @property
    def image_path(self):
        """``FieldFile.path``: the name resolved against the project root."""
        return os.path.join(current_app.config['BASE_DIR'], self.image)

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
