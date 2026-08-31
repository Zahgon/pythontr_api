"""Page-number pagination.

The shape of the paginated envelope is decided by ``core.pagination``; this
module only supplies the paging arithmetic and the ``next``/``previous`` link
building it reads, so that ``core.pagination`` can stay the small override it
has always been.
"""

import inspect
import math
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from flask import current_app, request as flask_request

from app.api import messages
from app.api.exceptions import NotFound
from app.api.response import Response


def replace_query_param(url, key, val):
    scheme, netloc, path, query, fragment = urlsplit(str(url))
    query_dict = parse_qs(query, keep_blank_values=True)
    query_dict[str(key)] = [str(val)]
    query = urlencode(sorted(query_dict.items()), doseq=True)
    return urlunsplit((scheme, netloc, path, query, fragment))


def remove_query_param(url, key):
    scheme, netloc, path, query, fragment = urlsplit(str(url))
    query_dict = parse_qs(query, keep_blank_values=True)
    query_dict.pop(str(key), None)
    query = urlencode(sorted(query_dict.items()), doseq=True)
    return urlunsplit((scheme, netloc, path, query, fragment))


def _takes_no_arguments(method):
    # ``list.count`` is callable but wants a value, so a page of an
    # already-materialised list would raise instead of falling through to
    # ``len()``.  Only a zero-argument ``count`` means "row count".
    if inspect.isbuiltin(method) or inspect.isbuiltin(
        getattr(method, '__func__', None)
    ):
        return False
    try:
        signature = inspect.signature(method)
    except (TypeError, ValueError):
        return False
    return not any(
        parameter.kind == parameter.POSITIONAL_OR_KEYWORD
        and parameter.default is parameter.empty
        for parameter in signature.parameters.values()
    )


class Paginator:

    def __init__(self, object_list, per_page, allow_empty_first_page=True):
        self.object_list = object_list
        self.per_page = int(per_page)
        self.allow_empty_first_page = allow_empty_first_page

    @property
    def count(self):
        counter = getattr(self.object_list, 'count', None)
        if callable(counter) and _takes_no_arguments(counter):
            return counter()
        return len(self.object_list)

    @property
    def num_pages(self):
        if self.count == 0 and not self.allow_empty_first_page:
            return 0
        return max(1, math.ceil(self.count / self.per_page))

    def validate_number(self, number):
        try:
            number = int(number)
        except (TypeError, ValueError):
            raise InvalidPage()
        if number < 1:
            raise InvalidPage()
        if number > self.num_pages:
            if number == 1 and self.allow_empty_first_page:
                pass
            else:
                raise InvalidPage()
        return number

    def page(self, number):
        number = self.validate_number(number)
        bottom = (number - 1) * self.per_page
        top = bottom + self.per_page
        if top > self.count:
            top = self.count
        return Page(list(self.object_list[bottom:top]), number, self)


class InvalidPage(Exception):
    pass


class Page:

    def __init__(self, object_list, number, paginator):
        self.object_list = object_list
        self.number = number
        self.paginator = paginator

    def __len__(self):
        return len(self.object_list)

    def __iter__(self):
        return iter(self.object_list)

    def __getitem__(self, index):
        return self.object_list[index]

    def has_next(self):
        return self.number < self.paginator.num_pages

    def has_previous(self):
        return self.number > 1

    def next_page_number(self):
        return self.number + 1

    def previous_page_number(self):
        return self.number - 1


class BasePagination:

    def paginate_queryset(self, queryset, request, view=None):
        raise NotImplementedError('paginate_queryset() must be implemented.')

    def get_paginated_response(self, data):
        raise NotImplementedError(
            'get_paginated_response() must be implemented.')


class PageNumberPagination(BasePagination):

    page_size = None
    page_query_param = 'page'
    last_page_strings = ('last',)
    paginator_class = Paginator

    def get_page_size(self, request):
        if self.page_size is not None:
            return self.page_size
        return current_app.config['PAGE_SIZE']

    def paginate_queryset(self, queryset, request, view=None):
        page_size = self.get_page_size(request)
        if not page_size:
            return None

        paginator = self.paginator_class(queryset, page_size)
        page_number = request.query_params.get(self.page_query_param) or 1
        if page_number in self.last_page_strings:
            page_number = paginator.num_pages

        try:
            self.page = paginator.page(page_number)
        except InvalidPage:
            raise NotFound(messages.INVALID_PAGE)

        self.request = request
        return list(self.page)

    def build_absolute_uri(self):
        return flask_request.url

    def get_next_link(self):
        if not self.page.has_next():
            return None
        url = self.build_absolute_uri()
        page_number = self.page.next_page_number()
        return replace_query_param(url, self.page_query_param, page_number)

    def get_previous_link(self):
        if not self.page.has_previous():
            return None
        url = self.build_absolute_uri()
        page_number = self.page.previous_page_number()
        if page_number == 1:
            return remove_query_param(url, self.page_query_param)
        return replace_query_param(url, self.page_query_param, page_number)

    def get_paginated_response(self, data):
        return Response({
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data,
        })
