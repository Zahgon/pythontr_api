"""The two authenticators.

``TokenAuthentication`` advertises the ``Token`` scheme, so a route whose FIRST
authenticator is this one answers 401 with ``WWW-Authenticate: Token`` when no credential
arrives. ``CookieTokenAuthentication`` advertises no scheme, so a route whose first
authenticator is that one answers 403 instead.
"""

import json
from urllib.parse import unquote

from sqlalchemy import select

from app.wire import AuthenticationFailed


class TokenAuthentication:
    keyword = 'Token'

    def authenticate_header(self, request):
        return self.keyword

    def authenticate(self, request, session):
        header = request.headers.get('authorization', '')
        if not header:
            return None
        parts = header.split()
        if not parts or parts[0] != self.keyword:
            return None
        if len(parts) == 1:
            raise AuthenticationFailed(
                'Geçersiz token başlığı. Kimlik bilgileri eksik.')
        if len(parts) > 2:
            raise AuthenticationFailed(
                "Geçersiz token başlığı. Token'da boşluk olmamalı.")
        return self.authenticate_credentials(parts[1], session)

    def authenticate_credentials(self, key, session):
        from core.models import Token
        token = session.scalar(select(Token).where(Token.key == key))
        if token is None:
            raise AuthenticationFailed('Geçersiz token.')
        if not token.user.is_active:
            raise AuthenticationFailed('Kullanıcı aktif değil ya da silinmiş.')
        return token.user, token.key


class CookieTokenAuthentication:
    """Reads a ``session`` cookie and resolves its token against the FRAMEWORK's own
    user table, which has no token relation at all -- so it never authenticates anybody
    and never raises either, because the lookup simply finds nothing. The cookie is still
    parsed, so a non-string token is reported.
    """

    def authenticate_header(self, request):
        return None

    def authenticate(self, request, session):
        token_data = request.cookies.get('session')
        if not token_data:
            return None
        try:
            decoded_data = unquote(token_data)
            token = json.loads(decoded_data).get('token')
            if not token:
                return None
            if not isinstance(token, str):
                raise AuthenticationFailed('Geçersiz token formatı.')
            return self.resolve(token, session)
        except (json.JSONDecodeError, AttributeError):
            return None

    def resolve(self, token, session):
        # The framework user table this used to query is not part of this project's
        # schema, so no row can ever match.
        return None
