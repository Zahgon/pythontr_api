from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

from .model_user import utcnow

# The content-type rows the old framework wrote for this project, frozen. They are schema,
# not fixtures: a comment's content_type_id already points at these numbers in production.
CONTENT_TYPE_IDS = (
    (1, 'admin', 'logentry'),
    (2, 'auth', 'permission'),
    (3, 'auth', 'group'),
    (4, 'contenttypes', 'contenttype'),
    (5, 'sessions', 'session'),
    (6, 'authtoken', 'token'),
    (7, 'authtoken', 'tokenproxy'),
    (8, 'core', 'user'),
    (9, 'core', 'category'),
    (10, 'core', 'article'),
    (11, 'core', 'comment'),
    (12, 'core', 'message'),
    (13, 'core', 'slider'),
    (14, 'core', 'pagevisit'),
    (15, 'core', 'activationcode'),
)

ARTICLE_CONTENT_TYPE_ID = 10
COMMENT_CONTENT_TYPE_ID = 11


def content_type_id_for(model):
    for pk, _app_label, name in CONTENT_TYPE_IDS:
        if name == model:
            return pk
    raise LookupError(model)


class ContentType(Base):
    __tablename__ = 'django_content_type'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    app_label: Mapped[str] = mapped_column(String(100), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)

    def __str__(self):
        return self.model


class Comment(Base):
    __tablename__ = 'core_comment'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    object_id: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    content: Mapped[str] = mapped_column(Text, nullable=False, default='')
    email: Mapped[str] = mapped_column(String(100), nullable=False, default='')
    name: Mapped[str] = mapped_column(String(50), nullable=False, default='')
    ip: Mapped[str] = mapped_column(String(100), nullable=False, default='')
    is_active: Mapped[bool] = mapped_column(nullable=False, default=False)
    is_delete: Mapped[bool] = mapped_column(nullable=False, default=False)
    content_type_id: Mapped[int] = mapped_column(ForeignKey('django_content_type.id'),
                                                 nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey('core_user.id'), nullable=True)

    content_type: Mapped['ContentType'] = relationship('ContentType', lazy='joined')

    @property
    def pk(self):
        return self.id

    def __str__(self):
        return self.content
