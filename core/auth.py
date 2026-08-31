"""Credential checking.

Stands in for ``django.contrib.auth.authenticate`` with the single backend the
project configured (``ModelBackend``), including its two quirks: an unknown
email still runs a password hash so timing does not leak account existence,
and an inactive user is rejected even when the password is right.
"""
from core.hashers import make_password
from core.models import User


def authenticate(request=None, username=None, password=None, **kwargs):
    if username is None:
        username = kwargs.get('email')
    if username is None or password is None:
        return None

    user = User.query.filter_by(email=username).one_or_none()
    if user is None:
        # Run the default password hasher once to reduce the timing
        # difference between an existing and a non-existing user.
        make_password(password)
        return None

    if user.check_password(password) and user_can_authenticate(user):
        return user

    return None


def user_can_authenticate(user):
    is_active = getattr(user, 'is_active', None)
    return is_active or is_active is None
