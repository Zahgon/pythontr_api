"""The ASGI application.

``app.main:app`` is the callable gunicorn and uvicorn serve, and it is the whole public
surface of the project: everything the API does is observable through it.
"""

from starlette.requests import Request
from starlette.routing import Route, Router

from app.middleware import (AllowHeaderMiddleware, CommonMiddleware,
                            ExceptionMiddleware,
                            FormatSuffixMiddleware, LocaleMiddleware,
                            SecurityMiddleware, SessionMiddleware,
                            XFrameOptionsMiddleware, not_found_response)
from recipe import routes as recipe_routes
from user import routes as user_routes
from user.admin import routes as admin_routes

#: Prefixes the trailing-slash redirect applies to.
KNOWN_PREFIXES = ('/api/',)

ALL_METHODS = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS']


def _endpoint(view):
    async def handler(request: Request):
        return await view(request)
    handler.__name__ = type(view).__name__
    return handler


def _route(path, view):
    return Route(path, _endpoint(view), methods=ALL_METHODS)


ROUTES = [
    # /api/recipe
    _route('/api/recipe/', recipe_routes.ApiRoot()),
    _route('/api/recipe/categories/', recipe_routes.CategoryCollection()),
    _route('/api/recipe/categories/{pk}/', recipe_routes.CategoryDetail()),
    _route('/api/recipe/articles/', recipe_routes.ArticleCollection()),
    _route('/api/recipe/articles/{pk}/', recipe_routes.ArticleDetail()),
    _route('/api/recipe/sliders/', recipe_routes.SliderCollection()),
    _route('/api/recipe/sliders/{pk}/', recipe_routes.SliderDetail()),
    _route('/api/recipe/comments/', recipe_routes.CommentCollection()),
    _route('/api/recipe/comments/{pk}/', recipe_routes.CommentDetail()),
    _route('/api/recipe/messages/', recipe_routes.MessageCollection()),
    _route('/api/recipe/messages/{pk}/', recipe_routes.MessageDetail()),
    # /api/user
    _route('/api/user/create/', user_routes.CreateUser()),
    _route('/api/user/token/', user_routes.CreateToken()),
    _route('/api/user/me/', user_routes.ManageUser()),
    _route('/api/user/activate/{code:uuid}/', user_routes.ActivateUser()),
    _route('/api/user/resend-activation/', user_routes.ResendActivation()),
    _route('/api/user/reset-password/', user_routes.PasswordReset()),
    _route('/api/user/reset-password/confirm/', user_routes.PasswordResetConfirm()),
    _route('/api/user/reset-password/confirm/{uidb64}/{token}/',
           user_routes.PasswordResetConfirm()),
    # /api/user/admin -- the staff JSON API. There is no server-rendered admin site.
    _route('/api/user/admin/', admin_routes.ApiRoot()),
    _route('/api/user/admin/users/', admin_routes.UserCollection()),
    _route('/api/user/admin/users/{pk}/', admin_routes.UserDetail()),
    _route('/api/user/admin/page-visits/', admin_routes.PageVisitCollection()),
    _route('/api/user/admin/page-visits/track_page_visit/',
           admin_routes.TrackPageVisit()),
    _route('/api/user/admin/page-visits/visitor_statistics/',
           admin_routes.VisitorStatistics()),
    _route('/api/user/admin/page-visits/content_performance/',
           admin_routes.ContentPerformance()),
    _route('/api/user/admin/page-visits/referrer_analysis/',
           admin_routes.ReferrerAnalysis()),
    _route('/api/user/admin/page-visits/{pk}/', admin_routes.PageVisitDetail()),
]


def resolves(path):
    """Does ``path`` match a registered route? The slash redirect needs to know."""
    for route in ROUTES:
        match, _ = route.matches({'type': 'http', 'path': path, 'method': 'GET',
                                  'path_params': {}})
        if match.value >= 2:
            return True
    return False


async def _not_found(scope, receive, send):
    """A routing miss renders the technical not-found page."""
    request = Request(scope, receive)
    response = not_found_response(request)
    await response(scope, receive, send)


def create_app():
    # A bare Router, not `Starlette`: the application class installs its own error
    # handler, which would answer a 500 before `ExceptionMiddleware` could render it.
    inner = Router(routes=ROUTES, redirect_slashes=False, default=_not_found)
    stack = AllowHeaderMiddleware(SessionMiddleware(FormatSuffixMiddleware(inner)))
    stack = ExceptionMiddleware(stack)
    stack = LocaleMiddleware(stack)
    stack = XFrameOptionsMiddleware(stack)
    stack = CommonMiddleware(stack)
    stack = SecurityMiddleware(stack)
    return inner, stack


application, app = create_app()
