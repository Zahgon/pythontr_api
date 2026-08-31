import json
from urllib.parse import unquote

from app.api import messages
from app.api.exceptions import AuthenticationFailed
from core.models import Token


class AnonymousUser:
    """The user attached to a request that carried no valid credentials."""

    id = None
    pk = None
    username = ''
    email = ''
    is_active = False
    is_staff = False
    is_superuser = False
    is_authenticated = False
    is_anonymous = True

    def __str__(self):
        return 'AnonymousUser'

    def __eq__(self, other):
        return isinstance(other, self.__class__)

    def __hash__(self):
        return hash(self.__class__)

    def __bool__(self):
        return True


class BaseAuthentication:

    def authenticate(self, request):
        raise NotImplementedError('.authenticate() must be overridden.')

    def authenticate_header(self, request):
        return None


class TokenAuthentication(BaseAuthentication):
    """``Authorization: Token <key>``, the scheme clients already send."""

    keyword = 'Token'
    model = Token

    def authenticate(self, request):
        auth = request.headers.get('Authorization', '')
        parts = auth.split()

        if not parts or parts[0] != self.keyword:
            return None
        if len(parts) == 1:
            raise AuthenticationFailed(
                messages.INVALID_TOKEN_HEADER_NO_CREDENTIALS)
        if len(parts) > 2:
            raise AuthenticationFailed(messages.INVALID_TOKEN_HEADER_SPACES)

        try:
            key = parts[1].decode() if isinstance(parts[1], bytes) \
                else parts[1]
        except UnicodeError:
            raise AuthenticationFailed(
                messages.INVALID_TOKEN_HEADER_CHARACTERS)

        return self.authenticate_credentials(key)

    def authenticate_credentials(self, key):
        token = self.model.query.filter_by(key=key).one_or_none()
        if token is None:
            raise AuthenticationFailed(messages.INVALID_TOKEN)
        if not token.user.is_active:
            raise AuthenticationFailed(messages.USER_INACTIVE_OR_DELETED)
        return (token.user, token)

    def authenticate_header(self, request):
        return self.keyword


class _SwappedManager:
    """Accessing this raises, exactly like the manager it stands in for.

    ``CookieTokenAuthentication`` below looks the token up on the framework's
    built-in user table.  That table has never been the one this project
    stores users in -- the project swapped in its own user model -- so the
    lookup has always failed at the manager access with an ``AttributeError``,
    which the ``except`` clause in ``authenticate`` then swallows.  The net
    effect is that cookie authentication has never authenticated anybody: it
    returns ``None`` for every request that carries a ``session`` cookie, and
    the request falls through to the next authenticator.

    Reproducing that dead path is deliberate.  Making the cookie work would
    change who can reach protected endpoints, which is a behaviour change, not
    a migration.
    """

    def __get__(self, instance, owner):
        raise AttributeError(
            "Manager isn't available; 'auth.User' has been swapped for "
            "'core.User'"
        )


class User:
    """The built-in user table this module refers to. See above."""

    objects = _SwappedManager()

    class DoesNotExist(Exception):
        pass


class CookieTokenAuthentication(BaseAuthentication):

    def authenticate(self, request):
        token_data = request.COOKIES.get('session')
        if not token_data:
            return None
        try:
            decoded_data = unquote(token_data)
            token = json.loads(decoded_data).get('token')
            if not token:
                return None
            if not isinstance(token, str):
                raise AuthenticationFailed(
                    messages.COOKIE_TOKEN_INVALID_FORMAT)
            user = User.objects.get(auth_token=token)
            if not user.is_active:
                raise AuthenticationFailed(messages.COOKIE_USER_INACTIVE)
            return (user, token)
        except (json.JSONDecodeError, AttributeError):
            return None
        except User.DoesNotExist:
            raise AuthenticationFailed(messages.COOKIE_TOKEN_INVALID)
