from datetime import datetime, timezone

from sqlalchemy import (Boolean, DateTime, ForeignKey, Integer, String, Text,
                        select)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app import security
from app.db import Base
from app.text import slugify


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def avatar_image_file_path(instance, filename):
    from app import settings
    f_name, ext = filename.split('.')
    allowed_chars = \
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._"
    sanitized_filename = ''.join(c for c in f_name if c in allowed_chars)
    slug = slugify(sanitized_filename)
    file_path = f'{settings.AVATAR_ROOT}{instance.pk}/{slug}.{ext}'
    return file_path


def validate_user(**kwargs):
    for key, value in kwargs.items():
        if not value:
            raise ValueError('Users must have an {} address'.format(value))


class User(Base):
    __tablename__ = 'core_user'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    password: Mapped[str] = mapped_column(String(128), nullable=False, default='')
    last_login: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    username: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, default='')
    surname: Mapped[str] = mapped_column(String(255), nullable=False, default='')
    image: Mapped[str] = mapped_column(String(100), nullable=True)
    about_me: Mapped[str] = mapped_column(Text, nullable=False, default='')
    linkedin: Mapped[str] = mapped_column(String(255), nullable=False, default='')
    github: Mapped[str] = mapped_column(String(255), nullable=False, default='')
    is_notification_email: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_staff: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_ban: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_delete: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    slug: Mapped[str] = mapped_column(String(150), nullable=False, unique=True, default='')
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)

    USERNAME_FIELD = 'email'

    @property
    def pk(self):
        return self.id

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_slug(self, session):
        """Pick a free slug.

        The row being saved is NOT excluded from the search, so saving an existing user
        again always finds its own slug taken and moves on to the next suffix.
        """
        slug = slugify(self.username.replace('ı', 'i'))
        unique = slug
        number = 1
        while session.scalar(select(User.id).where(User.slug == unique)) is not None:
            unique = '{}-{}'.format(slug, number)
            number += 1
        return unique

    def save(self, session):
        if not self.username:
            self.username = self.email.split('@')[0]
        self.updated_at = utcnow()
        self.slug = self.get_slug(session)
        if self.created_at is None:
            self.created_at = self.updated_at
        session.add(self)
        session.flush()
        return self

    def set_password(self, raw_password):
        self.password = security.make_password(raw_password)

    def check_password(self, raw_password):
        return security.check_password(raw_password, self.password)

    @property
    def image_url(self):
        from app import settings
        image_url = None
        if self.image:
            image_url = ('/%s' % self.image).replace(settings.APLICATION_NAME, '')
        return image_url

    def __str__(self):
        return self.email


class AnonymousUser:
    """The caller with no credentials. Falsy, and never authenticated."""

    id = None
    pk = None
    is_active = False
    is_staff = False
    is_superuser = False
    is_authenticated = False
    is_anonymous = True
    email = ''
    username = ''

    def __bool__(self):
        return False

    def __eq__(self, other):
        return isinstance(other, AnonymousUser)

    def __hash__(self):
        return hash('AnonymousUser')

    def __str__(self):
        return 'AnonymousUser'


class Token(Base):
    """The authentication token table the old framework owned."""

    __tablename__ = 'authtoken_token'

    key: Mapped[str] = mapped_column(String(40), primary_key=True)
    created: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    user_id: Mapped[int] = mapped_column(ForeignKey('core_user.id'), nullable=False,
                                         unique=True)

    user: Mapped['User'] = relationship('User', lazy='joined')

    @staticmethod
    def generate_key():
        return security.generate_token()


def create_user(session, email, password=None, **extra_fields):
    validate_user(email=email)
    user = User(email=normalize_email(email), **extra_fields)
    user.set_password(password)
    user.save(session)
    return user


def create_superuser(session, email, password):
    user = create_user(session, email, password)
    user.is_active = True
    user.is_staff = True
    user.is_superuser = True
    user.save(session)
    return user


def normalize_email(email):
    """Lower-case the domain half only, as the old manager did.

    An address carrying no ``@`` has no domain half to lower-case, so it is returned
    as it arrived; rejecting it is the validator's job, not this helper's.
    """
    email = email or ''
    stripped = email.strip()
    if '@' not in stripped:
        return email
    email_name, domain_part = stripped.rsplit('@', 1)
    return email_name + '@' + domain_part.lower()
