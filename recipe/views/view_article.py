from sqlalchemy.orm import joinedload

from app.api import mixins
from app.api.permissions import (IsAuthenticated,
                                 IsAuthenticatedOrReadOnly)
from app.api.response import Response
from app.api import status

from app.api.exceptions import NotFound
from flask_babel import gettext as _

from core import lookups
from core.models import Article

from recipe import serializers
from recipe.permissions import IsAuthenticatedAndOwner, \
    IsAuthenticatedAndOwnerOrAdmin

from .baseview import BaseViewSet
from .filter_param import RulesFilter, Search, Me, Category


class ArticleViewSet(BaseViewSet, mixins.CreateModelMixin):
    model = Article
    # Uploads came first in this view's parser list.
    parser_media_types = ('multipart/form-data',
                          'application/x-www-form-urlencoded',
                          'application/json')
    serializer_class = serializers.ArticleSerializer
    permission_classes_by_action = {
        'list': [IsAuthenticatedOrReadOnly],
        'retrieve': [IsAuthenticatedOrReadOnly],
        'create': [IsAuthenticated],
        'update': [IsAuthenticatedAndOwner],
        'destroy': [IsAuthenticatedAndOwnerOrAdmin],
    }

    def get_base_queryset(self):
        return Article.query.options(joinedload(Article.user))

    def get_object(self):
        id_or_slug = self.kwargs.get('pk')
        if id_or_slug.isdigit():
            return Article.query.filter_by(id=id_or_slug).one()
        return Article.query.filter_by(slug=id_or_slug).one()

    def get_queryset(self):
        """ self.action == 'list' """
        search = self.request.query_params.get('search', None)
        categories = self.request.query_params.getlist('category')
        is_active = self.request.query_params.get('is_active', None)
        me = self.request.query_params.get('me', None)
        queryset = None
        self.serializer_class = serializers.ArticleListSerializer

        SearchKwargs = {
            '{0}__{1}'.format('title', 'icontains'): search,
        }
        if categories:
            SearchKwargs['{0}__{1}'.format(
                'categories__id', 'in')] = categories

        MeKwargs = {
            '{0}'.format('user'): self.request.user,
            # **({'is_active': is_active == "true"} if is_active else {})
        }

        if is_active is not None:
            if is_active in ["true", "false"]:
                MeKwargs['is_active'] = is_active.lower() == "true"

        rules = [
            Search(search, **SearchKwargs),
            Category(categories, **SearchKwargs),
            Me(me, **MeKwargs)
        ]

        kwargs = {}

        if not me:
            kwargs['{0}_{1}'.format('is', 'active')] = True

        rf = RulesFilter(rules)
        for item in rf.get_res():
            if item.is_check():
                kwargs.update(item.get_param())

        queryset = lookups.apply(
            self.get_base_queryset(), Article, kwargs
        ).order_by(Article.id.desc()).distinct()

        if queryset.first() is None:
            raise NotFound(_('not_found'))

        return queryset

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        # Soft delete
        instance.is_delete = True
        instance.save()
        # Or hard delete
        # instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
