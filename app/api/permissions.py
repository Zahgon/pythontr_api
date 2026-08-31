"""Permission primitives.

The Django project leaned on ``rest_framework.permissions``.  The classes here
keep the same names, the same ``has_permission`` / ``has_object_permission``
protocol and, most importantly, the same 401-vs-403 behaviour: an anonymous
request that fails a permission check is reported as *not authenticated*, an
authenticated one as *permission denied*.
"""

SAFE_METHODS = ('GET', 'HEAD', 'OPTIONS')


class BasePermission:
    """Mirror of ``rest_framework.permissions.BasePermission``."""

    message = None

    def has_permission(self, request, view):
        return True

    def has_object_permission(self, request, view, obj):
        return True


class AllowAny(BasePermission):
    pass


class IsAuthenticated(BasePermission):

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)


class IsAdminUser(BasePermission):

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_staff)


class IsAuthenticatedOrReadOnly(BasePermission):

    def has_permission(self, request, view):
        return bool(
            request.method in SAFE_METHODS
            or (request.user and request.user.is_authenticated)
        )
