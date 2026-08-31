"""Query-string filter backends.

Two backends are used by the admin API: a free text ``?search=`` that scans a
list of columns, and an exact-match backend driven by ``?<field>=<value>`` for
the boolean flags on a user.
"""

from sqlalchemy import or_

#: The strings the boolean query parameters have always accepted.
BOOLEAN_TRUE = {'true', 'True', '1', 1, True}
BOOLEAN_FALSE = {'false', 'False', '0', 0, False}


def _is_boolean(column):
    try:
        return column.type.python_type is bool
    except NotImplementedError:
        return False


class BaseFilterBackend:

    def filter_queryset(self, request, queryset, view):
        raise NotImplementedError('.filter_queryset() must be overridden.')


class SearchFilter(BaseFilterBackend):
    """``?search=`` matched case-insensitively against ``search_fields``."""

    search_param = 'search'

    def get_search_terms(self, request):
        value = request.query_params.get(self.search_param, '')
        return value.replace('\x00', '').replace(',', ' ').split()

    def get_search_fields(self, view):
        return getattr(view, 'search_fields', None)

    def filter_queryset(self, request, queryset, view):
        search_fields = self.get_search_fields(view)
        search_terms = self.get_search_terms(request)
        if not search_fields or not search_terms:
            return queryset

        model = view.model
        for term in search_terms:
            clauses = [
                getattr(model, field).ilike('%{}%'.format(term))
                for field in search_fields
            ]
            queryset = queryset.filter(or_(*clauses))
        return queryset


class FieldFilterBackend(BaseFilterBackend):
    """Exact matches for the fields a view lists in ``filterset_fields``."""

    def get_filterset_fields(self, view):
        return getattr(view, 'filterset_fields', None) or []

    def filter_queryset(self, request, queryset, view):
        model = view.model
        for field in self.get_filterset_fields(view):
            if field not in request.query_params:
                continue
            raw = request.query_params.get(field)
            column = getattr(model, field)
            if _is_boolean(column):
                if raw in BOOLEAN_TRUE:
                    queryset = queryset.filter(column.is_(True))
                elif raw in BOOLEAN_FALSE:
                    queryset = queryset.filter(column.is_(False))
                else:
                    # An unparsable value makes the filter form invalid, and an
                    # invalid form has always produced an empty result set.
                    queryset = queryset.filter(False)
            else:
                queryset = queryset.filter(column == raw)
        return queryset
