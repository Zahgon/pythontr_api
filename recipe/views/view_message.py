from app.api import mixins
from app.api.permissions import IsAuthenticated

from sqlalchemy import or_

from core import lookups
from core.models import Message

from recipe import serializers
from recipe.permissions import IsAuthenticatedAndOwner

from .baseview import BaseViewSet
from .filter_param import RulesFilter, Search, Inbox, Outbox


class MessageViewSet(BaseViewSet, mixins.CreateModelMixin):
    model = Message
    serializer_class = serializers.MessageSerializer
    permission_classes_by_action = {
        'list': [IsAuthenticatedAndOwner],
        'retrieve': [IsAuthenticatedAndOwner],
        'create': [IsAuthenticated]
    }

    def get_base_queryset(self):
        return Message.objects.all()

    def get_queryset(self):
        search = self.request.query_params.get('search', None)
        inbox = self.request.query_params.get('inbox', None)
        outbox = self.request.query_params.get('outbox', None)
        queryset = None

        SearchKwargs = {
            '{0}__{1}'.format('subject', 'icontains'): search,
        }

        InboxKwargs = {
            '{0}'.format('user'): self.request.user,
        }

        OutboxKwargs = {
            '{0}'.format('sender'): self.request.user,
        }

        rules = [
            Search(search, **SearchKwargs),
            Inbox(inbox, **InboxKwargs),
            Outbox(outbox, **OutboxKwargs)
        ]

        kwargs = {
            '{0}_{1}'.format('is', 'delete'): False,
        }

        rf = RulesFilter(rules)
        for item in rf.get_res():
            if item.is_check():
                kwargs.update(item.get_param())

        queryset = lookups.apply(
            self.get_base_queryset(), Message, kwargs
        ).filter(
            or_(
                Message.user == self.request.user,
                Message.sender == self.request.user,
            )
        ).order_by(Message.id.desc()).distinct()

        return queryset
