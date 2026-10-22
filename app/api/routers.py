"""Turn a view set into URL rules.

A router knows the two shapes every collection in this API uses -- ``/prefix/``
for the collection and ``/prefix/<pk>/`` for a single row -- plus any
extra
routes a view set publishes with :func:`app.api.views.action`.  Registering a
view set therefore yields the same URLs, the same endpoint names and the same
API root document the project has always served.
"""

from collections import namedtuple

from flask import url_for

from app.api.permissions import AllowAny
from app.api.response import Response
from app.api.views import APIView

#: Every rule accepts every method: the view itself decides what is allowed so
#: that an anonymous request answers 401 before it can answer 405.
HTTP_METHODS = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS']

Route = namedtuple('Route', ['url', 'mapping', 'name', 'detail', 'initkwargs'])
DynamicRoute = namedtuple('DynamicRoute',
                          ['url', 'name', 'detail', 'initkwargs'])


class APIRootView(APIView):
    """The document listing every collection the router publishes."""

    # ``OPTIONS`` reported the previous framework's own docstring here.
    description = 'The default basic root view for DefaultRouter'
    permission_classes = (AllowAny,)
    api_root_dict = None
    name = 'Api Root'

    def get(self, request, **kwargs):
        data = {}
        for key, endpoint in self.api_root_dict.items():
            data[key] = url_for(endpoint, _external=True)
        return Response(data)


class SimpleRouter:

    routes = [
        Route(
            url=r'/{prefix}{trailing_slash}',
            mapping={'get': 'list', 'post': 'create'},
            name='{basename}-list',
            detail=False,
            initkwargs={'suffix': 'List'},
        ),
        DynamicRoute(
            url=r'/{prefix}/{url_path}{trailing_slash}',
            name='{basename}-{url_name}',
            detail=False,
            initkwargs={},
        ),
        Route(
            url=r'/{prefix}/{lookup}{trailing_slash}',
            mapping={
                'get': 'retrieve',
                'put': 'update',
                'patch': 'partial_update',
                'delete': 'destroy',
            },
            name='{basename}-detail',
            detail=True,
            initkwargs={'suffix': 'Instance'},
        ),
        DynamicRoute(
            url=r'/{prefix}/{lookup}/{url_path}{trailing_slash}',
            name='{basename}-{url_name}',
            detail=True,
            initkwargs={},
        ),
    ]

    def __init__(self, trailing_slash=True):
        self.registry = []
        self.trailing_slash = '/' if trailing_slash else ''

    def register(self, prefix, viewset, basename=None):
        if basename is None:
            basename = self.get_default_basename(viewset)
        self.registry.append((prefix, viewset, basename))

    def get_default_basename(self, viewset):
        model = getattr(viewset, 'model', None)
        assert model is not None, (
            '`basename` argument not specified, and could not automatically '
            'determine the name from the viewset, as it does not have a '
            '`.model` attribute.'
        )
        return model.__name__.lower()

    def get_routes(self, viewset):
        known_actions = set()
        for route in self.routes:
            if isinstance(route, Route):
                known_actions.update(route.mapping.values())

        extra_actions = viewset.get_extra_actions()
        for extra in extra_actions:
            assert extra.__name__ not in known_actions, (
                'Cannot use the @action decorator on the method "{}" as it is '
                'an existing route.'.format(extra.__name__)
            )

        detail_actions = [a for a in extra_actions if a.detail]
        list_actions = [a for a in extra_actions if not a.detail]

        routes = []
        for route in self.routes:
            if isinstance(route, DynamicRoute):
                source = detail_actions if route.detail else list_actions
                for extra in source:
                    routes.append(self._get_dynamic_route(route, extra))
            else:
                routes.append(route)
        return routes

    def _get_dynamic_route(self, route, extra):
        initkwargs = route.initkwargs.copy()
        initkwargs.update(extra.kwargs)
        return Route(
            url=route.url.replace('{url_path}', extra.url_path),
            mapping=extra.mapping,
            name=route.name.replace('{url_name}', extra.url_name),
            detail=route.detail,
            initkwargs=initkwargs,
        )

    def get_method_map(self, viewset, method_map):
        bound = {}
        for method, action_name in method_map.items():
            if hasattr(viewset, action_name):
                bound[method] = action_name
        return bound

    def get_lookup_rule(self, viewset):
        lookup_url_kwarg = (getattr(viewset, 'lookup_url_kwarg', None)
                            or getattr(viewset, 'lookup_field', 'pk'))
        return '<lookup:{}>'.format(lookup_url_kwarg)

    def get_urls(self):
        """Return ``(rule, endpoint, view_func)`` triples for a blueprint."""
        urls = []
        for prefix, viewset, basename in self.registry:
            lookup = self.get_lookup_rule(viewset)
            for route in self.get_routes(viewset):
                mapping = self.get_method_map(viewset, route.mapping)
                if not mapping:
                    continue
                url = route.url.format(
                    prefix=prefix,
                    lookup=lookup,
                    trailing_slash=self.trailing_slash,
                )
                initkwargs = route.initkwargs.copy()
                initkwargs.update({
                    'basename': basename,
                    'detail': route.detail,
                })
                view = viewset.as_view(mapping, **initkwargs)
                name = route.name.format(basename=basename)
                urls.append((url, name, view))
                urls.append((self.format_suffix_url(url), name + '-format',
                             view))
        return urls

    def format_suffix_url(self, url):
        """``/categories/`` also answers as ``/categories.json``."""
        return '{}.<string:format>'.format(url.rstrip('/'))

    def register_urls(self, blueprint):
        for url, name, view in self.get_urls():
            blueprint.add_url_rule(url, endpoint=name, view_func=view,
                                   methods=HTTP_METHODS)


class DefaultRouter(SimpleRouter):
    """A :class:`SimpleRouter` that also publishes the API root document."""

    APIRootView = APIRootView
    root_view_name = 'api-root'

    def get_api_root_view(self):
        api_root_dict = {}
        list_name = self.routes[0].name
        for prefix, viewset, basename in self.registry:
            # Endpoints are stored relative to the blueprint handling the
            # request.  A router can be mounted inside another blueprint --
            # the administration one is -- and only the request knows the
            # full dotted path that produces.
            api_root_dict[prefix] = '.{}'.format(
                list_name.format(basename=basename),
            )
        return self.APIRootView.as_view(api_root_dict=api_root_dict)

    def register_urls(self, blueprint):
        super().register_urls(blueprint)
        if not self.registry:
            return
        view = self.get_api_root_view()
        blueprint.add_url_rule('/', endpoint=self.root_view_name,
                               view_func=view, methods=HTTP_METHODS)
        blueprint.add_url_rule('/.<string:format>',
                               endpoint=self.root_view_name + '-format',
                               view_func=view, methods=HTTP_METHODS)
