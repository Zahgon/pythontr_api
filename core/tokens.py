"""Password reset token generation.

Reset links that were mailed out before the migration have to keep working
afterwards, so this is a faithful reimplementation of Django's
``default_token_generator`` rather than a new scheme: same salt, same HMAC
derivation, same base36 timestamp, same three day validity window.
"""
import base64
import binascii
import hashlib
import hmac
from datetime import datetime

from flask import current_app

BASE36_ALPHABET = '0123456789abcdefghijklmnopqrstuvwxyz'

# django.conf.global_settings.PASSWORD_RESET_TIMEOUT
PASSWORD_RESET_TIMEOUT = 60 * 60 * 24 * 3


def force_bytes(value, encoding='utf-8'):
    if isinstance(value, bytes):
        return value
    if not isinstance(value, str):
        value = str(value)
    return value.encode(encoding)


def force_str(value, encoding='utf-8'):
    if isinstance(value, str):
        return value
    if isinstance(value, bytes):
        return value.decode(encoding)
    return str(value)


def int_to_base36(i):
    if i < 0:
        raise ValueError('Negative base36 conversion input.')
    if i < 36:
        return BASE36_ALPHABET[i]
    b36 = ''
    while i != 0:
        i, n = divmod(i, 36)
        b36 = BASE36_ALPHABET[n] + b36
    return b36


def base36_to_int(s):
    if len(s) > 13:
        raise ValueError('Base36 input too large')
    return int(s, 36)


def urlsafe_base64_encode(s):
    return base64.urlsafe_b64encode(s).rstrip(b'\n=').decode('ascii')


def urlsafe_base64_decode(s):
    s = s.encode()
    try:
        return base64.urlsafe_b64decode(
            s.ljust(len(s) + len(s) % 4, b'=')
        )
    except (LookupError, binascii.Error) as e:
        raise ValueError(e)


def salted_hmac(key_salt, value, secret=None, algorithm='sha1'):
    if secret is None:
        secret = current_app.config['SECRET_KEY']
    key_salt = force_bytes(key_salt)
    secret = force_bytes(secret)
    hasher = getattr(hashlib, algorithm)
    key = hasher(key_salt + secret).digest()
    return hmac.new(key, msg=force_bytes(value), digestmod=hasher)


class PasswordResetTokenGenerator:
    key_salt = 'django.contrib.auth.tokens.PasswordResetTokenGenerator'
    algorithm = 'sha256'
    secret = None

    def make_token(self, user):
        return self._make_token_with_timestamp(
            user,
            self._num_seconds(self._now()),
            self._get_secret()
        )

    def check_token(self, user, token):
        if not (user and token):
            return False
        try:
            ts_b36, _ = token.split('-')
        except ValueError:
            return False

        try:
            ts = base36_to_int(ts_b36)
        except ValueError:
            return False

        expected = self._make_token_with_timestamp(
            user, ts, self._get_secret()
        )
        if not hmac.compare_digest(expected, token):
            return False

        if (self._num_seconds(self._now()) - ts) > PASSWORD_RESET_TIMEOUT:
            return False

        return True

    def _get_secret(self):
        return self.secret or current_app.config['SECRET_KEY']

    def _make_token_with_timestamp(self, user, timestamp, secret):
        ts_b36 = int_to_base36(timestamp)
        hash_string = salted_hmac(
            self.key_salt,
            self._make_hash_value(user, timestamp),
            secret=secret,
            algorithm=self.algorithm,
        ).hexdigest()[::2]
        return '%s-%s' % (ts_b36, hash_string)

    def _make_hash_value(self, user, timestamp):
        login_timestamp = (
            '' if user.last_login is None
            else user.last_login.replace(microsecond=0, tzinfo=None)
        )
        email = getattr(user, 'email', '') or ''
        return f'{user.pk}{user.password}{login_timestamp}{timestamp}{email}'

    def _num_seconds(self, dt):
        return int((dt - datetime(2001, 1, 1)).total_seconds())

    def _now(self):
        return datetime.now()


default_token_generator = PasswordResetTokenGenerator()
