import uuid
from datetime import datetime, timedelta

from sqlalchemy import DateTime, ForeignKey, Integer, String, select, update
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

from .model_user import utcnow


class ActivationCode(Base):
    __tablename__ = 'core_activationcode'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('core_user.id'), nullable=False)
    code: Mapped[str] = mapped_column(String(32), nullable=False,
                                      default=lambda: uuid.uuid4().hex)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    is_used: Mapped[bool] = mapped_column(nullable=False, default=False)

    user = relationship('User', lazy='joined')

    @property
    def pk(self):
        return self.id

    @property
    def is_expired(self):
        return utcnow() > self.expires_at

    @classmethod
    def create_activation_code(cls, session, user):
        session.execute(update(cls)
                        .where(cls.user_id == user.id, cls.is_used.is_(False))
                        .values(is_used=True))
        activation = cls(user_id=user.id, code=uuid.uuid4().hex,
                         created_at=utcnow(),
                         expires_at=utcnow() + timedelta(hours=24),
                         is_used=False)
        session.add(activation)
        session.flush()
        return activation
