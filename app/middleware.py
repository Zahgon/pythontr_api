"""The middleware stack, nested in the order ``settings.MIDDLEWARE`` lists.

Outermost first: security headers, then the host check and the trailing-slash redirect,
then the frame header, then the locale header. The nesting is observable, because a layer
that answers from ``process_request`` leaves the layers INSIDE it unrun: an
``APPEND_SLASH`` redirect and a disallowed host both carry the security headers and
neither carries ``X-Frame-Options``, ``Content-Language`` or ``Vary``.
"""

from starlette.datastructures import MutableHeaders
from starlette.responses import RedirectResponse, Response

from app import pages
from app.urls import split_format_suffix
from app.wire import ApiError, error_response, get_allow


class _HeaderMiddleware:
    """Adds headers to the response of whatever it wraps."""

    def __init__(self, app):
        self.app = app

    def headers_for(self, scope):
        return {}

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return
        extra = self.headers_for(scope)

        async def send_wrapper(message):
            if message['type'] == 'http.response.start':
                headers = MutableHeaders(scope=message)
                for key, value in extra.items():
                    headers[key] = value
            await send(message)

        await self.app(scope, receive, send_wrapper)


class SecurityMiddleware(_HeaderMiddleware):
    def headers_for(self, scope):
        return {'X-Content-Type-Options': 'nosniff',
                'Referrer-Policy': 'same-origin',
                'Cross-Origin-Opener-Policy': 'same-origin'}


class XFrameOptionsMiddleware(_HeaderMiddleware):
    def headers_for(self, scope):
        from app import settings
        return {'X-Frame-Options': settings.X_FRAME_OPTIONS}


class AllowHeaderMiddleware:
    """Writes the verb set the route recorded.

    It sits INSIDE the exception layer, so a response the exception layer renders -- the
    technical 500 page -- carries no ``Allow`` even though the route had recorded one,
    while every response a route produced carries it, 401, 403, 405 and 204 included.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return

        async def send_wrapper(message):
            if message['type'] == 'http.response.start':
                allow = scope.get('allow')
                if allow:
                    MutableHeaders(scope=message)['Allow'] = allow
            await send(message)

        await self.app(scope, receive, send_wrapper)


class LocaleMiddleware:
    """Stamps ``Content-Language`` and folds ``Accept-Language`` into ``Vary``.

    The existing ``Vary`` value decides where the new token goes: it is inserted after the
    first entry, so a view that varies on ``Accept, Cookie`` ends up with
    ``Accept, Accept-Language, Cookie`` and a response with no ``Vary`` at all ends up
    with ``Accept-Language`` alone.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return
        from app import settings

        async def send_wrapper(message):
            if message['type'] == 'http.response.start':
                headers = MutableHeaders(scope=message)
                headers['Content-Language'] = settings.LANGUAGE_CODE
                existing = headers.get('Vary')
                if existing:
                    parts = [part.strip() for part in existing.split(',') if part.strip()]
                    parts.insert(1, 'Accept-Language')
                    headers['Vary'] = ', '.join(parts)
                else:
                    headers['Vary'] = 'Accept-Language'
            await send(message)

        await self.app(scope, receive, send_wrapper)


class CommonMiddleware:
    """The host check and the ``APPEND_SLASH`` redirect.

    Both answer here, so neither reaches the layers inside this one.
    """

    def __init__(self, app):
        self.app = app

    def _host_allowed(self, host, allowed):
        host = (host or '').split(':')[0].lower()
        for pattern in allowed:
            pattern = pattern.strip().lower()
            if pattern == '*' or pattern == host:
                return True
            if pattern.startswith('.') and (host.endswith(pattern)
                                            or host == pattern[1:]):
                return True
        return False

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return
        from app import settings
        headers = dict((key.decode('latin-1').lower(), value.decode('latin-1'))
                       for key, value in scope.get('headers', []))
        host = headers.get('host', '')
        method = scope.get('method', 'GET')
        path = scope.get('path', '/')
        if not self._host_allowed(host, settings.ALLOWED_HOSTS):
            body = pages.bad_request_page(method, 'http://%s%s' % (host, path))
            response = Response(body, status_code=400,
                                media_type='text/html; charset=utf-8')
            await response(scope, receive, send)
            return
        if settings.APPEND_SLASH and not path.endswith('/') and self._should_redirect(path):
            query = scope.get('query_string', b'').decode('latin-1')
            target = path + '/'
            if query:
                target = '%s?%s' % (target, query)
            response = RedirectResponse(target, status_code=301)
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)

    def _should_redirect(self, path):
        """As before: redirect only when this path does not resolve and the slashed one
        does. A path carrying a format suffix resolves on its own, so it is left alone."""
        from app.main import resolves
        if split_format_suffix(path)[1] is not None:
            return False
        if resolves(path):
            return False
        return resolves(path + '/')


class FormatSuffixMiddleware:
    """Takes a ``.json`` or ``.api`` suffix off the path and records it on the scope."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] == 'http':
            path, suffix = split_format_suffix(scope['path'])
            scope['format_suffix'] = suffix
            if suffix:
                scope['path'] = path
                scope['raw_path'] = path.encode('latin-1')
        await self.app(scope, receive, send)


class SessionMiddleware:
    """One database session per request, closed before the response is finished.

    Nothing is carried from one request to the next: no identity map, no pending state and
    no open transaction, so two requests cannot see each other's half-written rows.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return
        from app.db import new_session
        session = new_session()
        scope['db'] = session
        try:
            await self.app(scope, receive, send)
            session.commit()
        except BaseException:
            session.rollback()
            raise
        finally:
            session.close()


class ExceptionMiddleware:
    """Renders an API error as a JSON envelope and anything else as the 500 page."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return
        try:
            await self.app(scope, receive, send)
        except ApiError as error:
            response = error_response(error)
            await response(scope, receive, send)
        except Exception as exc:  # the technical 500 page, as before
            url = 'http://%s%s' % (
                dict((k.decode('latin-1').lower(), v.decode('latin-1'))
                     for k, v in scope.get('headers', [])).get('host', ''),
                scope.get('path', '/'))
            body = pages.server_error_page(scope.get('method', 'GET'), url,
                                           type(exc).__name__)
            response = Response(body, status_code=500,
                                media_type='text/html; charset=utf-8')
            await response(scope, receive, send)


def not_found_response(request):
    """The technical not-found page a routing miss renders."""
    body = pages.not_found_page(request.method, str(request.url))
    return Response(body, status_code=404, media_type='text/html; charset=utf-8')
