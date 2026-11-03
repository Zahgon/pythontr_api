"""The common request pipeline every route runs.

Order, which is observable: the advertised verb set is recorded, then the renderer is
selected, then the caller is identified, then permissions are checked, and only then is
the method looked at. So an anonymous caller on a known path with an unsupported verb is
answered 401 or 403 rather than 405, while an identified one gets the 405.
"""

from app import browsable, negotiation
from app.authentication import CookieTokenAuthentication, TokenAuthentication
from app.wire import (JSONResponse, ApiError, MethodNotAllowed, NotAuthenticated,
                      PermissionDenied, json_response, set_allow)
from core.models import AnonymousUser

#: ``API['DEFAULT_AUTHENTICATION_CLASSES']`` lists the cookie one first.
DEFAULT_AUTHENTICATORS = (CookieTokenAuthentication, TokenAuthentication)
#: The recipe routes and ``/api/user/me/`` put the token one first instead.
TOKEN_FIRST_AUTHENTICATORS = (TokenAuthentication, CookieTokenAuthentication)

ALLOW_ANY = 'allow_any'
IS_AUTHENTICATED = 'is_authenticated'
IS_ADMIN = 'is_admin'
IS_AUTHENTICATED_OR_READ_ONLY = 'is_authenticated_or_read_only'
SAFE_METHODS = ('GET', 'HEAD', 'OPTIONS')


class View:
    """One endpoint. Subclasses declare ``allow``, ``permissions`` and handlers."""

    allow = 'GET, HEAD, OPTIONS'
    authenticators = DEFAULT_AUTHENTICATORS
    #: method -> permission rule; a method absent from the map falls back to ``default``.
    permissions = {}
    default_permission = IS_AUTHENTICATED
    title = 'Api Root'

    async def __call__(self, request):
        set_allow(request, self.allow)
        try:
            renderer = negotiation.selected(request)
            session = request.scope['db']
            user = self.identify(request, session)
            request.scope['user'] = user
            self.check_permission(request, user)
            payload, status_code, extra = await self.handle(request, session, user)
        except ApiError as error:
            extra = {}
            scheme = getattr(error, 'scheme', None)
            if scheme:
                extra['WWW-Authenticate'] = scheme
            return self.render(request, negotiation.JSON, error.body(),
                               error.status_code, extra)
        return self.render(request, renderer, payload, status_code, extra)

    # --- identity ---------------------------------------------------------------
    def identify(self, request, session):
        for authenticator_class in self.authenticators:
            result = authenticator_class().authenticate(request, session)
            if result is not None:
                return result[0]
        return AnonymousUser()

    def unauthenticated(self, request):
        """401 when the first authenticator advertises a scheme, 403 when it does not."""
        first = self.authenticators[0]()
        scheme = first.authenticate_header(request)
        if scheme:
            error = NotAuthenticated()
            error.scheme = scheme
            return error
        return NotAuthenticated(status_code=403)

    def check_permission(self, request, user):
        rule = self.permissions.get(request.method, self.default_permission)
        if rule == ALLOW_ANY:
            return
        if rule == IS_AUTHENTICATED_OR_READ_ONLY and request.method in SAFE_METHODS:
            return
        if not user.is_authenticated:
            raise self.unauthenticated(request)
        if rule == IS_ADMIN and not user.is_staff:
            raise PermissionDenied()

    # --- dispatch ---------------------------------------------------------------
    async def handle(self, request, session, user):
        method = request.method
        if method == 'HEAD':
            method = 'GET'
        handler = getattr(self, method.lower(), None)
        if handler is None or method not in self.allow.replace(' ', '').split(','):
            if method == 'OPTIONS':
                return self.options_payload(), 200, {}
            raise MethodNotAllowed(request.method)
        return await handler(request, session, user)

    def options_payload(self):
        return {'name': self.title, 'renders': ['application/json', 'text/html'],
                'parses': ['application/json', 'application/x-www-form-urlencoded',
                           'multipart/form-data']}

    # --- rendering --------------------------------------------------------------
    def render(self, request, renderer, payload, status_code, extra):
        headers = {}
        vary = 'Accept'
        if renderer == negotiation.API:
            vary = 'Accept, Cookie'
        headers['Vary'] = vary
        headers.update(extra or {})
        if status_code == 204:
            return json_response(None, status_code=204, headers=headers)
        if renderer == negotiation.API:
            body = browsable.render(request, payload, status_code, self.title)
            headers['Content-Type'] = browsable.MEDIA_TYPE
            from starlette.responses import Response
            response = Response(body, status_code=status_code, headers=headers,
                                media_type='text/html; charset=utf-8')
            response.set_cookie(browsable.CSRF_COOKIE, browsable.new_csrf_token(),
                                path='/', samesite='lax')
            return response
        return JSONResponse(payload, status_code=status_code, headers=headers)
