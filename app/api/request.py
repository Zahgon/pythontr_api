"""The request object the views see.

Flask exposes the raw WSGI environ; the views in this project were written
against a richer request (parsed body, authenticated user, query parameters).
Subclassing ``flask.Request`` keeps those call sites unchanged instead of
threading helpers through every view.
"""
import json

from flask import Request, g
from werkzeug.datastructures import CombinedMultiDict, MultiDict

from app.api.exceptions import ParseError, UnsupportedMediaType

JSON_CONTENT_TYPES = ('application/json', 'application/json-patch+json')
FORM_CONTENT_TYPES = (
    'application/x-www-form-urlencoded',
    'multipart/form-data',
)


class APIRequest(Request):

    @property
    def user(self):
        from app.authentication import AnonymousUser

        return getattr(g, 'user', None) or AnonymousUser()

    @property
    def auth(self):
        return getattr(g, 'auth', None)

    @property
    def successful_authenticator(self):
        return getattr(g, 'successful_authenticator', None)

    @property
    def force_auth_user(self):
        """Set by the test client to bypass the authentication classes.

        The tests sign in users that ``TokenAuthentication`` would refuse --
        ``create_user`` leaves ``is_active`` false -- so the credentials have
        to be short-circuited rather than supplied.
        """
        return self.environ.get('app.force_auth_user')

    @property
    def force_auth_token(self):
        return self.environ.get('app.force_auth_token')

    @property
    def query_params(self):
        return self.args

    @property
    def META(self):
        return self.environ

    @property
    def COOKIES(self):
        return self.cookies

    @property
    def data(self):
        """JSON body when sent as JSON, otherwise form fields plus uploads.

        A body in any other content type is refused rather than read as an
        empty payload: the original API answered 415 there, and silently
        seeing no fields would turn that into a validation error instead.
        A body of zero length is the exception -- it never reached a parser,
        so an empty payload is what the fields saw whatever the header said.
        """
        if not self.content_length:
            return MultiDict()
        media_type = self.mimetype
        if media_type in JSON_CONTENT_TYPES:
            try:
                return json.loads(self.get_data().decode('utf-8'))
            except ValueError as exc:
                raise ParseError('JSON parse error - %s' % str(exc))
        if media_type in FORM_CONTENT_TYPES:
            return CombinedMultiDict([self.form, self.files])
        raise UnsupportedMediaType(media_type)


class ForcedAuthentication:
    """Stands in for the real authentication classes under test.

    Mirrors what the previous framework's test client did: rather than
    fabricating credentials, it swaps the whole authenticator list for one
    that always succeeds with the requested user.
    """

    def __init__(self, force_user, force_token):
        self.force_user = force_user
        self.force_token = force_token

    def authenticate(self, request):
        return (self.force_user, self.force_token)

    def authenticate_header(self, request):
        return None
