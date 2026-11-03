from datetime import datetime

from sqlalchemy import (DateTime, ForeignKey, Integer, SmallInteger, String,
                        Text, select)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.text import slugify

from .model_user import utcnow


class Category(Base):
    __tablename__ = 'core_category'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    title_h1: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=True)
    short_name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    slug: Mapped[str] = mapped_column(String(150), nullable=False, unique=True, default='')
    sort: Mapped[int] = mapped_column(SmallInteger, nullable=True, default=0)
    user_id: Mapped[int] = mapped_column(ForeignKey('core_user.id'), nullable=True)
    parent_category_id: Mapped[int] = mapped_column(ForeignKey('core_category.id'),
                                                    nullable=True)

    parent_category: Mapped['Category'] = relationship(
        'Category', remote_side=[id], back_populates='categories', lazy='selectin')
    categories: Mapped[list['Category']] = relationship(
        'Category', back_populates='parent_category', lazy='selectin',
        order_by='Category.id')

    @property
    def pk(self):
        return self.id

    def get_slug(self, session):
        """As with a user, the row being saved is not excluded from the search."""
        slug = slugify(self.name.replace('ı', 'i'))
        unique = slug
        number = 1
        while session.scalar(select(Category.id).where(Category.slug == unique)) is not None:
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

    @property
    def full_category_name(self):
        return self.__str__()

    def __str__(self):
        full_path = [self.name]
        k = self.parent_category
        while k is not None:
            full_path.append(k.name)
            k = k.parent_category
        return ' / '.join(full_path[::-1])
