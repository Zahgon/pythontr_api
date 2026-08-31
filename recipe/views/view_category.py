from app.api import mixins
from app.api.permissions import (IsAuthenticatedOrReadOnly,
                                 IsAdminUser)

from core import lookups
from core.models import Category

from recipe import serializers

from .baseview import BaseViewSet
from .filter_param import RulesFilter, Search


class CategoryViewSet(BaseViewSet, mixins.CreateModelMixin):
    model = Category
    serializer_class = serializers.CategorySerializer
    permission_classes_by_action = {'create': [IsAdminUser],
                                    'list': [IsAuthenticatedOrReadOnly],
                                    'retrieve': [IsAuthenticatedOrReadOnly]}

    def get_object(self):
        id_or_slug = self.kwargs.get('pk')
        if id_or_slug.isdigit():
            return Category.query.filter_by(id=id_or_slug).one()
        return Category.query.filter_by(slug=id_or_slug).one()

    def get_queryset(self):
        search = self.request.query_params.get('search')
        queryset = None

        SearchKwargs = {
            '{0}__{1}'.format('name', 'icontains'): search,
        }

        rules = [
            Search(search, **SearchKwargs),
        ]

        kwargs = {}

        rf = RulesFilter(rules)

        for item in rf.get_res():
            if item.is_check():
                kwargs.update(item.get_param())

        queryset = lookups.apply(
            self.get_base_queryset(), Category, kwargs
        ).all()
        queryset = sorted(queryset, key=lambda x: x.full_category_name)
        return queryset
