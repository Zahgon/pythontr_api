from app.extensions import db

from .base import SaveMixin, now


class PageVisit(db.Model, SaveMixin):
    __tablename__ = 'core_pagevisit'
    __app_label__ = 'core'

    id = db.Column(db.BigInteger().with_variant(db.Integer, 'sqlite'),
                   primary_key=True)
    user_id = db.Column(
        db.BigInteger().with_variant(db.Integer, 'sqlite'),
        db.ForeignKey('core_user.id', ondelete='CASCADE'),
        nullable=True,
    )
    path = db.Column(db.String(255), nullable=False, default='')
    content_id = db.Column(db.Integer, nullable=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=now)
    ip_address = db.Column(db.String(39), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)
    referrer = db.Column(db.String(500), nullable=True)
    METHOD_CHOICES = [
        ('GET', 'GET'),
        ('POST', 'POST'),
        ('PUT', 'PUT'),
        ('DELETE', 'DELETE'),
        ('PATCH', 'PATCH'),
    ]
    method = db.Column(db.String(10), nullable=False)
    DEVICE_TYPE_CHOICES = [
        ('mobile', 'mobile'),
        ('tablet', 'tablet'),
        ('desktop', 'desktop'),
    ]
    device_type = db.Column(db.String(50), nullable=False, default='unknown')
    language = db.Column(db.String(10), nullable=True, default='en')
    browser = db.Column(db.String(50), nullable=True)
    os = db.Column(db.String(50), nullable=True)
    device_brand = db.Column(db.String(50), nullable=True)
    device_model = db.Column(db.String(50), nullable=True)

    ga_client_id = db.Column(db.String(100), nullable=True)
    ga_session_id = db.Column(db.String(100), nullable=True)

    gads_id = db.Column(db.String(100), nullable=True)
    gpi_uid = db.Column(db.String(100), nullable=True)

    __table_args__ = (
        db.Index('core_pagevi_timesta_9a6d5c_idx', 'timestamp'),
        db.Index('core_pagevi_device__4dd8d5_idx', 'device_type'),
        db.Index('core_pagevi_ip_addr_2ee1e0_idx', 'ip_address'),
    )

    #: ``Meta.ordering`` — every read of this table is newest-first.
    default_ordering = (timestamp.desc(),)

    user = db.relationship('User')

    @property
    def pk(self):
        return self.id

    def save(self, *args, **kwargs):
        if self.timestamp is None:
            self.timestamp = now()
        return super(PageVisit, self).save()

    def __str__(self):
        return f"{self.user} visited {self.path} at {self.timestamp}"
