"""Password hashing and signed tokens.

Every row in ``core_user.password`` was written by the old stack, so the encoding here is
the same one: ``pbkdf2_sha256$<iterations>$<salt>$<base64>`` over a SHA-256 digest with a
22-character ``$``-free salt. A hash stored at a lower iteration count still verifies and
is re-hashed in place at the current count.
"""

import base64
import binascii
import datetime
import hashlib
import hmac
import secrets

ALGORITHM = 'pbkdf2_sha256'
ITERATIONS = 600000
SALT_ENTROPY = 128
UNUSABLE_PASSWORD_PREFIX = '!'
UNUSABLE_PASSWORD_SUFFIX_LENGTH = 40
PASSWORD_RESET_TIMEOUT = 259200
RANDOM_STRING_CHARS = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
KEY_SALT = 'django.contrib.auth.tokens.PasswordResetTokenGenerator'
_EPOCH = datetime.datetime(2001, 1, 1)


def get_random_string(length, allowed_chars=RANDOM_STRING_CHARS):
    return ''.join(secrets.choice(allowed_chars) for _ in range(length))


def salt():
    """A 22-character salt, which is what the stored rows carry."""
    return get_random_string(22, RANDOM_STRING_CHARS)


def force_bytes(value, encoding='utf-8'):
    if isinstance(value, bytes):
        return value
    return str(value).encode(encoding)


def constant_time_compare(left, right):
    return hmac.compare_digest(force_bytes(left), force_bytes(right))


def pbkdf2(password, salt_value, iterations, digest=hashlib.sha256):
    return hashlib.pbkdf2_hmac(digest().name, force_bytes(password),
                               force_bytes(salt_value), int(iterations))


def make_password(password, salt_value=None, iterations=ITERATIONS):
    if password is None:
        return UNUSABLE_PASSWORD_PREFIX + get_random_string(
            UNUSABLE_PASSWORD_SUFFIX_LENGTH)
    salt_value = salt_value or salt()
    if '$' in salt_value:
        raise ValueError('salt must not contain $')
    digest = pbkdf2(password, salt_value, iterations)
    encoded = base64.b64encode(digest).decode('ascii').strip()
    return '%s$%d$%s$%s' % (ALGORITHM, iterations, salt_value, encoded)


def is_password_usable(encoded):
    return encoded is None or not encoded.startswith(UNUSABLE_PASSWORD_PREFIX)


def check_password(password, encoded, setter=None):
    """Verify ``password``. ``setter`` is called when the stored count is stale."""
    if password is None or not encoded or not is_password_usable(encoded):
        return False
    try:
        algorithm, iterations, salt_value, _digest = encoded.split('$', 3)
    except ValueError:
        return False
    if algorithm != ALGORITHM:
        return False
    correct = constant_time_compare(
        encoded, make_password(password, salt_value, int(iterations)))
    if correct and setter is not None and int(iterations) != ITERATIONS:
        setter(password)
    return correct


def generate_token():
    """A 40-character lower-case hexadecimal authentication token."""
    return binascii.hexlify(secrets.token_bytes(20)).decode()


def salted_hmac(key_salt, value, secret, algorithm='sha256'):
    hasher = getattr(hashlib, algorithm)
    key = hasher(force_bytes(key_salt) + force_bytes(secret)).digest()
    return hmac.new(key, msg=force_bytes(value), digestmod=hasher)


def urlsafe_base64_encode(value):
    return base64.urlsafe_b64encode(force_bytes(value)).rstrip(b'\n=').decode('ascii')


def urlsafe_base64_decode(value):
    value = force_bytes(value)
    return base64.urlsafe_b64decode(value.ljust(len(value) + len(value) % 4, b'='))


def int_to_base36(number):
    if number < 0:
        raise ValueError('Negative base36 conversion input.')
    digits = '0123456789abcdefghijklmnopqrstuvwxyz'
    if number < 36:
        return digits[number]
    result = ''
    while number:
        number, index = divmod(number, 36)
        result = digits[index] + result
    return result


def base36_to_int(value):
    if len(value) > 13:
        raise ValueError('Base36 input too large')
    return int(value, 36)


class PasswordResetTokenGenerator:
    """``<timestamp-base36>-<hash>``, invalidated by a password change or a login."""

    key_salt = KEY_SALT
    algorithm = 'sha256'
    secret = None

    def __init__(self, secret=None):
        self.secret = secret

    def _secret(self):
        if self.secret is not None:
            return self.secret
        from app import settings
        return settings.SECRET_KEY

    def _now(self):
        return datetime.datetime.now()

    def _num_seconds(self, moment):
        return int((moment - _EPOCH).total_seconds())

    def _hash_value(self, user, timestamp):
        login_timestamp = ('' if user.last_login is None
                           else user.last_login.replace(microsecond=0, tzinfo=None))
        return '%s%s%s%s%s' % (user.pk, user.password, login_timestamp, timestamp,
                               user.email)

    def _make_token_with_timestamp(self, user, timestamp):
        digest = salted_hmac(self.key_salt, self._hash_value(user, timestamp),
                             secret=self._secret(),
                             algorithm=self.algorithm).hexdigest()[::2]
        return '%s-%s' % (int_to_base36(timestamp), digest)

    def make_token(self, user):
        return self._make_token_with_timestamp(user, self._num_seconds(self._now()))

    def check_token(self, user, token):
        if not (user and token):
            return False
        try:
            timestamp_b36, _ = token.split('-')
            timestamp = base36_to_int(timestamp_b36)
        except ValueError:
            return False
        if not constant_time_compare(
                self._make_token_with_timestamp(user, timestamp), token):
            return False
        if (self._num_seconds(self._now()) - timestamp) > PASSWORD_RESET_TIMEOUT:
            return False
        return True


default_token_generator = PasswordResetTokenGenerator()
