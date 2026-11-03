from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

from .model_user import utcnow


class Message(Base):
    __tablename__ = 'core_message'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    sender_id: Mapped[int] = mapped_column(ForeignKey('core_user.id'), nullable=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('core_user.id'), nullable=True)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    ip: Mapped[str] = mapped_column(String(100), nullable=False)
    is_read: Mapped[bool] = mapped_column(nullable=False, default=False)
    is_delete: Mapped[bool] = mapped_column(nullable=False, default=False)
    is_sender_delete: Mapped[bool] = mapped_column(nullable=False, default=False)

    sender = relationship('User', foreign_keys=[sender_id], lazy='joined')
    user = relationship('User', foreign_keys=[user_id], lazy='joined')

    @property
    def pk(self):
        return self.id

    def __str__(self):
        return self.subject


def visible_messages():
    """The default message query. Soft-deleted rows are invisible to every caller."""
    return select(Message).where(Message.is_delete.is_(False))
