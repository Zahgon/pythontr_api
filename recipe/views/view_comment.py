from app.api import mixins
from app.api.permissions import AllowAny

from core import lookups
from core.models import Article, Comment, ContentType

from recipe.permissions import IsAuthenticatedAndOwner

from recipe import serializers

from .baseview import BaseViewSet
from .filter_param import RulesFilter, Search


class CommentViewSet(
    BaseViewSet,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
):
    model = Comment
    serializer_class = serializers.CommentSerializer
    permission_classes_by_action = {'create': [AllowAny],
                                    'list': [AllowAny],
                                    'update': [IsAuthenticatedAndOwner],
                                    'partial_update': [IsAuthenticatedAndOwner]
                                    }

    def get_queryset(self):
        article_content_type = ContentType.get_for_model(Article)
        comment_content_type = ContentType.get_for_model(Comment)
        search = self.request.query_params.get('search')
        queryset = []
        SearchKwargs = {
            '{0}__{1}'.format('name', 'icontains'): search,
        }

        rules = [
            Search(search, **SearchKwargs)
        ]

        base_kwargs = {
            '{0}_{1}'.format('is', 'active'): True,
            '{0}_{1}'.format('is', 'delete'): False,
        }

        comment_type = self.request.query_params.get('comment_type', 'article')
        parent_id = self.request.query_params.get('parent_id')

        if comment_type == 'article':
            base_kwargs.update({
                '{0}_{1}'.format('content', 'type'): article_content_type,
                '{0}__{1}'.format('object_id', 'in'): Article.query.filter_by(
                    is_active=True,
                    is_delete=False
                ).all(),
            })
        elif comment_type == 'comment':
            base_kwargs.update({
                '{0}_{1}'.format('content', 'type'): comment_content_type,
            })

            if parent_id:
                base_kwargs['{0}'.format('object_id')] = parent_id

        rf = RulesFilter(rules)
        for item in rf.get_res():
            if item.is_check():
                base_kwargs.update(item.get_param())

        queryset = lookups.apply(
            self.get_base_queryset(), Comment, base_kwargs
        ).order_by(Comment.id.desc())

        return queryset

    def perform_create(self, serializer):
        if self.request.user.is_anonymous:
            # save anyone
            serializer.save()
        else:
            serializer.save(user=self.request.user)
