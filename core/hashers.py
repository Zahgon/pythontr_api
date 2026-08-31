"""Password hashing, kept bit-compatible with Django's default hasher.

The deployed database stores ``pbkdf2_sha256$<iterations>$<salt>$<hash>``
strings produced by ``django.contrib.auth.hashers.PBKDF2PasswordHasher``.
Switching to Werkzeug's format would have invalidated every existing password,
so the algorithm is reimplemented here instead of swapped out.
"""
import base64
import hashlib
import secrets

ALGORITHM = 'pbkdf2_sha256'
ITERATIONS = 600000
DIGEST = hashlib.sha256
SALT_ENTROPY = 128
RANDOM_STRING_CHARS = (
    'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
)
UNUSABLE_PASSWORD_PREFIX = '!'
UNUSABLE_PASSWORD_SUFFIX_LENGTH = 40


def get_random_string(length, allowed_chars=RANDOM_STRING_CHARS):
    return ''.join(secrets.choice(allowed_chars) for _ in range(length))


def salt():
    """Same entropy budget Django uses (128 bits over 62 symbols)."""
    char_count = len(RANDOM_STRING_CHARS)
    char_bits = (len(bin(char_count - 1)) - 2)
    salt_len = -(-SALT_ENTROPY // char_bits)
    return get_random_string(salt_len, RANDOM_STRING_CHARS)


def encode(password, salt_value=None, iterations=ITERATIONS):
    salt_value = salt_value or salt()
    if '$' in salt_value:
        raise ValueError('salt must not contain $')
    digest = hashlib.pbkdf2_hmac(
        DIGEST().name, password.encode(), salt_value.encode(), iterations
    )
    hashed = base64.b64encode(digest).decode('ascii').strip()
    return '%s$%d$%s$%s' % (ALGORITHM, iterations, salt_value, hashed)


def make_password(password):
    if password is None:
        return UNUSABLE_PASSWORD_PREFIX + get_random_string(
            UNUSABLE_PASSWORD_SUFFIX_LENGTH
        )
    return encode(password)


def is_password_usable(encoded):
    return encoded is None or not encoded.startswith(UNUSABLE_PASSWORD_PREFIX)


def check_password(password, encoded):
    if password is None or not is_password_usable(encoded):
        return False
    try:
        algorithm, iterations, salt_value, _ = encoded.split('$', 3)
    except ValueError:
        return False
    if algorithm != ALGORITHM:
        return False
    candidate = encode(password, salt_value, int(iterations))
    return secrets.compare_digest(candidate.encode(), encoded.encode())
