from flask import current_app

from app.extensions import db
from core import hashers, storage
from core.text import slugify

from .base import Manager, SaveMixin, now, unique_slug


def avatar_image_file_path(instance, filename):
    f_name, ext = filename.split('.')
    allowed_chars = \
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._"
    sanitized_filename = ''.join(c for c in f_name if c in allowed_chars)
    slug = slugify(sanitized_filename)
    avatar_root = current_app.config['AVATAR_ROOT']
    file_path = f'{avatar_root}{instance.pk}/{slug}.{ext}'
    return file_path


def validate_user(**kwargs):
    for key, value in kwargs.items():
        if not value:
            raise ValueError('Users must have an {} address'.format(value))


class UserManager(Manager):
    """Stand-in for ``User.objects``.

    Django's manager is what the codebase reached for when it needed
    ``create_user`` / ``create_superuser``; keeping the same entry points means
    the views, serializers and tests call it the same way they always did.
    """

    @staticmethod
    def normalize_email(email):
        """``BaseUserManager.normalize_email``: lowercase the domain only."""
        email = email or ''
        try:
            email_name, domain_part = email.strip().rsplit('@', 1)
        except ValueError:
            pass
        else:
            email = email_name + '@' + domain_part.lower()
        return email

    def create_user(self, email, password=None, **extra_fields):
        validate_user(email=email)
        user = self.model(email=self.normalize_email(email), **extra_fields)
        user.set_password(password)
        user.save()

        return user

    def create_superuser(self, email, password):
        user = self.create_user(email, password)

        user.is_active = True
        user.is_staff = True
        user.is_superuser = True
        user.save()

        return user


class User(db.Model, SaveMixin):
    __tablename__ = 'core_user'
    __app_label__ = 'core'

    id = db.Column(db.BigInteger().with_variant(db.Integer, 'sqlite'),
                   primary_key=True)
    password = db.Column(db.String(128), nullable=False, default='')
    last_login = db.Column(db.DateTime, nullable=True)
    is_superuser = db.Column(db.Boolean, nullable=False, default=False)
    email = db.Column(db.String(255), nullable=False, unique=True)
    username = db.Column(db.String(255), nullable=False, unique=True)
    name = db.Column(db.String(255), nullable=False, default='')
    surname = db.Column(db.String(255), nullable=False, default='')
    image = db.Column(db.String(100), nullable=True)
    about_me = db.Column(db.Text, nullable=False, default='')
    linkedin = db.Column(db.String(255), nullable=False, default='')
    github = db.Column(db.String(255), nullable=False, default='')
    is_notification_email = db.Column(db.Boolean, nullable=False, default=True)
    is_active = db.Column(db.Boolean, nullable=False, default=False)
    is_staff = db.Column(db.Boolean, nullable=False, default=False)
    is_ban = db.Column(db.Boolean, nullable=False, default=False)
    is_delete = db.Column(db.Boolean, nullable=False, default=False)
    slug = db.Column(db.String(150), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, nullable=False, default=now)
    updated_at = db.Column(db.DateTime, nullable=False, default=now)

    auth_token = db.relationship(
        'Token', back_populates='user', uselist=False,
        cascade='all, delete-orphan',
    )

    USERNAME_FIELD = 'email'

    def __init__(self, **kwargs):
        kwargs.setdefault('password', '')
        kwargs.setdefault('name', '')
        kwargs.setdefault('surname', '')
        kwargs.setdefault('about_me', '')
        kwargs.setdefault('linkedin', '')
        kwargs.setdefault('github', '')
        super().__init__(**kwargs)

    @property
    def pk(self):
        return self.id

    # -- authentication ---------------------------------------------------
    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)

    def set_password(self, raw_password):
        self.password = hashers.make_password(raw_password)

    def check_password(self, raw_password):
        return hashers.check_password(raw_password, self.password)

    # -- Django's model hooks ---------------------------------------------
    def get_slug(self):
        return unique_slug(User, User.slug, self.username)

    def save(self, *args, **kwargs):
        if not self.username:
            self.username = self.email.split('@')[0]
        self.updated_at = now()
        if self.created_at is None:
            self.created_at = self.updated_at
        self.slug = self.get_slug()
        self.image = storage.persist(self, self.image, avatar_image_file_path)

        return super(User, self).save()

    @property
    def image_url(self):
        image_url = None
        if self.image:
            image_url = self.image.replace(
                current_app.config['APLICATION_NAME'], ''
            )
        return image_url

    def __str__(self):
        """``AbstractBaseUser.__str__`` returned ``get_username()``."""
        return self.email


User.objects = UserManager(User)
