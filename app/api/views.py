"""Class based views.

The project is organised around view sets: a class exposes ``list``,
``retrieve``, ``create``… and a router turns those into URL rules.  A
request is
authenticated first, then checked against the view's permissions, and only then
routed to a handler -- so an anonymous call to an unsupported method answers
401 rather than 405, which is what the API has always done.
"""

import inspect
import re

from flask import current_app, g
from flask import request as flask_request
from werkzeug.utils import import_string

from app.api import status
from app.api.exceptions import (APIException, AuthenticationFailed,
                                MethodNotAllowed, NotAuthenticated,
                                PermissionDenied)
from app.api.permissions import AllowAny
from app.api.request import ForcedAuthentication
from app.api.response import Response

UNSET = object()


class APIView:

    authentication_classes = None
    permission_classes = (AllowAny,)
    http_method_names = ['get', 'post', 'put', 'patch', 'delete', 'head',
                         'options']

    def __init__(self, **initkwargs):
        for key, value in initkwargs.items():
            setattr(self, key, value)

    @classmethod
    def as_view(cls, **initkwargs):
        def view(**kwargs):
            instance = cls(**initkwargs)
            return instance.dispatch(flask_request, **kwargs)

        view.view_class = cls
        view.view_initkwargs = initkwargs
        view.__name__ = cls.__name__
        view.__doc__ = cls.__doc__
        return view

    def setup(self, request, **kwargs):
        if hasattr(self, 'get') and not hasattr(self, 'head'):
            self.head = self.get
        self.request = request
        self.kwargs = kwargs

    @property
    def allowed_methods(self):
        return [method.upper() for method in self.http_method_names
                if hasattr(self, method)]

    @property
    def default_response_headers(self):
        return {
            'Allow': ', '.join(self.allowed_methods),
            'Vary': 'Accept',
        }

    def get_authenticators(self):
        request = getattr(self, 'request', None)
        forced_user = getattr(request, 'force_auth_user', None)
        forced_token = getattr(request, 'force_auth_token', None)
        if forced_user is not None or forced_token is not None:
            return [ForcedAuthentication(forced_user, forced_token)]
        classes = self.authentication_classes
        if classes is None:
            classes = current_app.config['DEFAULT_AUTHENTICATION_CLASSES']
        return [_resolve(item)() for item in classes]

    def get_permissions(self):
        return [permission() for permission in self.permission_classes]

    def perform_authentication(self, request):
        self.authenticators = self.get_authenticators()
        g.user = None
        g.auth = None
        g.successful_authenticator = None
        for authenticator in self.authenticators:
            result = authenticator.authenticate(request)
            if result is not None:
                g.user, g.auth = result
                g.successful_authenticator = authenticator
                return

    def check_permissions(self, request):
        for permission in self.get_permissions():
            if not permission.has_permission(request, self):
                self.permission_denied(
                    request, message=getattr(permission, 'message', None),
                )

    def check_object_permissions(self, request, obj):
        for permission in self.get_permissions():
            if not permission.has_object_permission(request, self, obj):
                self.permission_denied(
                    request, message=getattr(permission, 'message', None),
                )

    def permission_denied(self, request, message=None):
        if self.authenticators and not request.successful_authenticator:
            raise NotAuthenticated()
        raise PermissionDenied(detail=message)

    def initial(self, request, **kwargs):
        self.perform_authentication(request)
        self.check_permissions(request)

    def http_method_not_allowed(self, request, **kwargs):
        raise MethodNotAllowed(request.method)

    def get_authenticate_header(self, request):
        authenticators = self.get_authenticators()
        if authenticators:
            return authenticators[0].authenticate_header(request)
        return None

    def handle_exception(self, exc):
        if isinstance(exc, (NotAuthenticated, AuthenticationFailed)):
            # Only the first authenticator names a challenge scheme, and a
            # failure without one answers 403 rather than 401.  Which one a
            # view returns therefore depends on the order it lists its
            # authenticators in -- the cookie one names nothing, so every
            # view that lists it first answers 403 where the others answer
            # 401 plus ``WWW-Authenticate``.
            auth_header = self.get_authenticate_header(self.request)
            if auth_header:
                exc.auth_header = auth_header
            else:
                exc.status_code = status.HTTP_403_FORBIDDEN
        if isinstance(exc, APIException):
            return Response(exc.get_body(), status=exc.status_code,
                            headers=exc.get_headers())
        raise exc

    def finalize_response(self, response):
        for key, value in self.headers.items():
            response.headers.setdefault(key, value)
        return response.to_flask_response()

    def dispatch(self, request, **kwargs):
        self.format_kwarg = kwargs.pop('format', None)
        self.setup(request, **kwargs)
        self.headers = self.default_response_headers
        try:
            self.initial(request, **kwargs)
            method = request.method.lower()
            if method in self.http_method_names:
                handler = getattr(self, method, self.http_method_not_allowed)
            else:
                handler = self.http_method_not_allowed
            response = handler(request, **kwargs)
        except APIException as exc:
            response = self.handle_exception(exc)
        return self.finalize_response(response)

    def get_view_name(self):
        name = getattr(self, 'name', None)
        if name is not None:
            return name
        name = self.__class__.__name__
        name = re.sub('ViewSet$', '', name)
        name = re.sub('View$', '', name)
        name = re.sub(r'(?<=[a-z0-9])([A-Z])', r' \1', name).strip()
        suffix = getattr(self, 'suffix', None)
        if suffix:
            name = '{} {}'.format(name, suffix)
        return name

    def get_view_description(self):
        description = getattr(self, 'description', None)
        if description is not None:
            return description
        return (self.__class__.__doc__ or '').strip()

    def options(self, request, **kwargs):
        data = {
            'name': self.get_view_name(),
            'description': self.get_view_description(),
            'renders': ['application/json', 'text/html'],
            'parses': [
                'application/json',
                'application/x-www-form-urlencoded',
                'multipart/form-data',
            ],
        }
        return Response(data, status=status.HTTP_200_OK)


class GenericAPIView(APIView):

    model = None
    queryset = None
    serializer_class = None
    lookup_field = 'id'
    lookup_url_kwarg = 'pk'
    filter_backends = ()
    pagination_class = UNSET

    def get_base_queryset(self):
        """The view's unfiltered queryset.

        Django evaluated the ``queryset`` class attribute at import time; a
        SQLAlchemy ``Model.query`` needs an application context, so the base
        queryset is built here instead and the ``model`` attribute carries the
        part the router needs at import time.
        """
        if self.queryset is not None:
            return self.queryset
        assert self.model is not None, (
            '{} should either include a `model` attribute, or override the '
            '`get_queryset()` method.'.format(self.__class__.__name__)
        )
        return self.model.query

    def get_queryset(self):
        return self.get_base_queryset()

    def filter_queryset(self, queryset):
        for backend in self.filter_backends:
            queryset = backend().filter_queryset(self.request, queryset, self)
        return queryset

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        lookup = self.kwargs[lookup_url_kwarg]
        obj = queryset.filter_by(**{self.lookup_field: lookup}).one()
        self.check_object_permissions(self.request, obj)
        return obj

    def get_serializer_class(self):
        assert self.serializer_class is not None, (
            '{} should either include a `serializer_class` attribute, or '
            'override the `get_serializer_class()` method.'.format(
                self.__class__.__name__)
        )
        return self.serializer_class

    def get_serializer_context(self):
        return {'request': self.request, 'view': self}

    def get_serializer(self, *args, **kwargs):
        serializer_class = self.get_serializer_class()
        kwargs.setdefault('context', self.get_serializer_context())
        return serializer_class(*args, **kwargs)

    def get_pagination_class(self):
        if self.pagination_class is not UNSET:
            return self.pagination_class
        if current_app.config.get('TESTING'):
            return None
        path = current_app.config.get('DEFAULT_PAGINATION_CLASS')
        return import_string(path) if path else None

    @property
    def paginator(self):
        if not hasattr(self, '_paginator'):
            pagination_class = self.get_pagination_class()
            self._paginator = (
                None if pagination_class is None else pagination_class()
            )
        return self._paginator

    def paginate_queryset(self, queryset):
        if self.paginator is None:
            return None
        return self.paginator.paginate_queryset(queryset, self.request, self)

    def get_paginated_response(self, data):
        return self.paginator.get_paginated_response(data)


class CreateModelMixin:

    def create(self, request, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_create(self, serializer):
        serializer.save()


class ListModelMixin:

    def list(self, request, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class RetrieveModelMixin:

    def retrieve(self, request, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class UpdateModelMixin:

    def update(self, request, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(
            instance, data=request.data, partial=partial,
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def partial_update(self, request, **kwargs):
        kwargs['partial'] = True
        return self.update(request, **kwargs)

    def perform_update(self, serializer):
        serializer.save()


class DestroyModelMixin:

    def destroy(self, request, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_destroy(self, instance):
        instance.delete()


class CreateAPIView(CreateModelMixin, GenericAPIView):

    def post(self, request, **kwargs):
        return self.create(request, **kwargs)


class RetrieveUpdateAPIView(RetrieveModelMixin, UpdateModelMixin,
                            GenericAPIView):

    def get(self, request, **kwargs):
        return self.retrieve(request, **kwargs)

    def put(self, request, **kwargs):
        return self.update(request, **kwargs)

    def patch(self, request, **kwargs):
        return self.partial_update(request, **kwargs)


def action(methods=None, detail=False, url_path=None, url_name=None, **kwargs):
    """Mark a view set method as an extra route the router should publish."""
    methods = ['get'] if methods is None else methods

    def decorator(func):
        func.mapping = {method.lower(): func.__name__ for method in methods}
        func.detail = detail
        func.url_path = url_path if url_path else func.__name__
        func.url_name = url_name if url_name else func.__name__.replace(
            '_', '-')
        func.kwargs = kwargs
        return func

    return decorator


def _is_extra_action(attr):
    return hasattr(attr, 'mapping') and hasattr(attr, 'detail')


class ViewSetMixin:

    @classmethod
    def as_view(cls, actions=None, **initkwargs):
        actions = dict(actions or {})
        if 'get' in actions and 'head' not in actions:
            actions['head'] = actions['get']

        def view(**kwargs):
            instance = cls(**initkwargs)
            instance.action_map = actions
            for method, handler_name in actions.items():
                handler = getattr(instance, handler_name, None)
                if handler is not None:
                    setattr(instance, method, handler)
            return instance.dispatch(flask_request, **kwargs)

        view.view_class = cls
        view.view_initkwargs = initkwargs
        view.actions = actions
        view.__name__ = cls.__name__
        view.__doc__ = cls.__doc__
        return view

    def setup(self, request, **kwargs):
        self.action = getattr(self, 'action_map', {}).get(
            request.method.lower())
        super().setup(request, **kwargs)

    @classmethod
    def get_extra_actions(cls):
        return [method for _, method
                in inspect.getmembers(cls, _is_extra_action)]


class ViewSet(ViewSetMixin, APIView):
    pass


class GenericViewSet(ViewSetMixin, GenericAPIView):
    pass


class ReadOnlyModelViewSet(RetrieveModelMixin, ListModelMixin, GenericViewSet):
    pass


class ModelViewSet(CreateModelMixin, RetrieveModelMixin, UpdateModelMixin,
                   DestroyModelMixin, ListModelMixin, GenericViewSet):
    pass


def _resolve(item):
    return import_string(item) if isinstance(item, str) else item
