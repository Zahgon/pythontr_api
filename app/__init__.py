"""Application factory.

``manage.py``, ``app.wsgi`` and the test suite all build the application
through
:func:`create_app`; nothing imports a module-level application object.
"""
import os
from urllib.parse import urlsplit, urlunsplit

from flask import Flask, current_app, g, request
from werkzeug.http import HTTP_STATUS_CODES, http_date
from werkzeug.routing import BaseConverter, RequestRedirect

from app import settings
from app.api.request import APIRequest
from app.authentication import AnonymousUser
from app.extensions import babel, db, login_manager, migrate


class LookupConverter(BaseConverter):
    """URL segment that stops at ``/`` and ``.``.

    The router appends ``.<format>`` suffix rules next to every route, so the
    primary-key segment must not swallow the dot.
    """

    regex = r'[^/.]+'


def relative_location(location):
    parts = urlsplit(location)
    return urlunsplit(('', '', parts.path, parts.query, parts.fragment))


def select_locale():
    languages = list(current_app.config['LANGUAGES'])
    return (request.accept_languages.best_match(languages) or
            current_app.config['BABEL_DEFAULT_LOCALE'])


def create_app(config=None):
    app = Flask(
        __name__,
        static_folder=os.path.join(settings.BASE_DIR, 'static'),
        static_url_path=settings.Config.STATIC_URL.rstrip('/'),
    )
    app.config.from_object(config or settings.get_config())
    app.url_map.converters['lookup'] = LookupConverter
    # A repeated slash used to be a miss rather than something to tidy up, so
    # collapsing them here would turn 404s into redirects.
    app.url_map.merge_slashes = False
    app.request_class = APIRequest
    # Serializers emit their fields in declaration order; sorting would reorder
    # every response body.
    app.json.sort_keys = False

    db.init_app(app)
    migrate.init_app(
        app, db, directory=os.path.join(settings.BASE_DIR, 'migrations')
    )
    babel.init_app(app, locale_selector=select_locale)
    # The cross-origin extension is installed but deliberately not started:
    # the project has always shipped the dependency without ever adding it to
    # the request pipeline, so no ``Access-Control-*`` header is emitted.
    login_manager.init_app(app)

    from core import admin as core_admin, cli
    from core.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    core_admin.register(app)
    cli.register(app)

    from app.urls import register_blueprints
    register_blueprints(app)

    @app.before_request
    def set_anonymous_user():
        g.user = AnonymousUser()
        g.auth = None
        g.successful_authenticator = None

    @app.after_request
    def add_response_headers(response):
        appended_slash = isinstance(
            request.routing_exception, RequestRedirect
        )
        response.headers.setdefault('X-Content-Type-Options', 'nosniff')
        response.headers.setdefault('Referrer-Policy', 'same-origin')
        response.headers.setdefault(
            'Cross-Origin-Opener-Policy', 'same-origin'
        )
        if not appended_slash:
            # The trailing-slash redirect was produced ahead of the
            # clickjacking and language layers, so it never collected their
            # headers; the three above ran before it and did.
            response.headers.setdefault('X-Frame-Options', 'DENY')
            response.headers.setdefault(
                'Content-Language', str(select_locale())
            )
            vary = response.headers.get('Vary')
            response.headers['Vary'] = (
                '{}, Accept-Language'.format(vary) if vary
                else 'Accept-Language'
            )
        if response.status_code == 308:
            # The only 308 this application can produce is the routing layer
            # appending a missing trailing slash, and that answered 301.
            response.status_code = 301
        if request.path.startswith('/admin/'):
            # Every administration page was served with caching switched off.
            response.headers['Expires'] = http_date()
            response.headers['Cache-Control'] = (
                'max-age=0, no-cache, no-store, must-revalidate, private'
            )
        if response.location:
            # A redirect carried a bare path and an empty body; the absolute
            # URL and the explanatory document are this framework's additions.
            response.headers['Location'] = relative_location(
                response.location
            )
            response.set_data(b'')
        if request.method == 'HEAD':
            # A reply to HEAD went out without a length header; werkzeug
            # derives one during finalisation unless it is told not to, and
            # popping alone is undone at that point.
            response.automatically_set_content_length = False
            response.headers.pop('Content-Length', None)
        reason = HTTP_STATUS_CODES.get(response.status_code)
        if reason:
            # Werkzeug upper-cases the reason phrase it derives from a status
            # code; the phrase is part of the status line clients read back.
            response.status = '{} {}'.format(response.status_code, reason)
        return response

    return app
