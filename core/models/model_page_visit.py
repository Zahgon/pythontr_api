from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

from .model_user import utcnow

METHOD_CHOICES = [
    ('GET', 'GET'),
    ('POST', 'POST'),
    ('PUT', 'PUT'),
    ('DELETE', 'DELETE'),
    ('PATCH', 'PATCH'),
]

DEVICE_TYPE_CHOICES = [
    ('mobile', 'mobile'),
    ('tablet', 'tablet'),
    ('desktop', 'desktop'),
]


class PageVisit(Base):
    __tablename__ = 'core_pagevisit'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('core_user.id'), nullable=True)
    path: Mapped[str] = mapped_column(String(255), nullable=False)
    content_id: Mapped[int] = mapped_column(Integer, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    ip_address: Mapped[str] = mapped_column(String(39), nullable=True)
    user_agent: Mapped[str] = mapped_column(Text, nullable=True)
    referrer: Mapped[str] = mapped_column(String(500), nullable=True)
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    # 'unknown' is not a member of DEVICE_TYPE_CHOICES. It is the default the column was
    # created with, so it stays.
    device_type: Mapped[str] = mapped_column(String(50), nullable=False, default='unknown')
    language: Mapped[str] = mapped_column(String(10), nullable=True, default='en')
    browser: Mapped[str] = mapped_column(String(50), nullable=True)
    os: Mapped[str] = mapped_column(String(50), nullable=True)
    device_brand: Mapped[str] = mapped_column(String(50), nullable=True)
    device_model: Mapped[str] = mapped_column(String(50), nullable=True)
    ga_client_id: Mapped[str] = mapped_column(String(100), nullable=True)
    ga_session_id: Mapped[str] = mapped_column(String(100), nullable=True)
    gads_id: Mapped[str] = mapped_column(String(100), nullable=True)
    gpi_uid: Mapped[str] = mapped_column(String(100), nullable=True)

    user = relationship('User', lazy='joined')

    __table_args__ = (
        Index('core_pagevisit_timestamp_idx', 'timestamp'),
        Index('core_pagevisit_device_type_idx', 'device_type'),
        Index('core_pagevisit_ip_address_idx', 'ip_address'),
    )

    @property
    def pk(self):
        return self.id

    def __str__(self):
        return f"{self.user} visited {self.path} at {self.timestamp}"
