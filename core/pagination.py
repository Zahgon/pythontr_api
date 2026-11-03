"""The page envelope.

The arithmetic and the link rewriting live in :func:`app.wire.paginate`; this module keeps
the names the settings file points at.
"""

from app.wire import PAGE_QUERY_PARAM, page_size, paginate  # noqa: F401


def relative(link):
    """Reduce an absolute link to a path, as the old class did with ``split('/', 3)``."""
    if not link:
        return None
    return '/{}'.format(link.split('/', 3)[-1])


class CustomPagination:
    """``settings.API['DEFAULT_PAGINATION_CLASS']`` points here."""

    page_query_param = PAGE_QUERY_PARAM

    @property
    def page_size(self):
        return page_size()

    def get_paginated_response(self, request, rows, serialize):
        return paginate(request, rows, serialize)
