"""The four configured password validators.

Nothing in the request path calls them, exactly as before: a five-character password is
still accepted by the account routes. They are configured in
``settings.AUTH_PASSWORD_VALIDATORS`` and are available to management work.

``UserAttributeSimilarityValidator.validate(password, user)`` reads only ``user.email``
and ``user.username``; any object carrying those two attributes is accepted.
"""

import difflib
import gzip
import os
import re


class ValidationError(Exception):
    def __init__(self, message, code=None, params=None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.params = params or {}

    def __str__(self):
        return str(self.message)


class UserAttributeSimilarityValidator:
    DEFAULT_USER_ATTRIBUTES = ('email', 'username')

    def __init__(self, user_attributes=DEFAULT_USER_ATTRIBUTES, max_similarity=0.7):
        self.user_attributes = user_attributes
        self.max_similarity = max(max_similarity, 0.1)

    def validate(self, password, user=None):
        if not user:
            return
        password = password.lower()
        for attribute_name in self.user_attributes:
            value = getattr(user, attribute_name, None)
            if not value or not isinstance(value, str):
                continue
            value_parts = re.split(r'\W+', value) + [value]
            for value_part in value_parts:
                if difflib.SequenceMatcher(
                        a=password, b=value_part.lower()).quick_ratio() >= self.max_similarity:
                    raise ValidationError(
                        'The password is too similar to the %s.' % attribute_name,
                        code='password_too_similar',
                        params={'verbose_name': attribute_name})


class MinimumLengthValidator:
    def __init__(self, min_length=8):
        self.min_length = min_length

    def validate(self, password, user=None):
        if len(password) < self.min_length:
            raise ValidationError('This password is too short.',
                                  code='password_too_short',
                                  params={'min_length': self.min_length})


class CommonPasswordValidator:
    # The shipped list, kept small enough to read and wide enough to catch the usual
    # choices. The old stack read a gzipped list from its own package, which is gone.
    DEFAULT_PASSWORD_LIST = (
        'password', 'password1', '123456', '12345678', '123456789', '1234567890',
        'qwerty', 'qwerty123', 'abc123', 'letmein', 'monkey', 'dragon', 'football',
        'iloveyou', 'admin', 'welcome', 'login', 'princess', 'solo', 'master',
        'sunshine', 'baseball', 'shadow', 'michael', 'superman', 'trustno1',
    )

    def __init__(self, password_list_path=None):
        self.passwords = set(self.DEFAULT_PASSWORD_LIST)
        if password_list_path and os.path.exists(password_list_path):
            opener = gzip.open if str(password_list_path).endswith('.gz') else open
            with opener(password_list_path, 'rt', encoding='utf-8') as handle:
                self.passwords = {line.strip() for line in handle}

    def validate(self, password, user=None):
        if password.lower().strip() in self.passwords:
            raise ValidationError('This password is too common.',
                                  code='password_too_common')


class NumericPasswordValidator:
    def validate(self, password, user=None):
        if password.isdigit():
            raise ValidationError('This password is entirely numeric.',
                                  code='password_entirely_numeric')
