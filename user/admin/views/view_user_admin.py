from app.api import viewsets, status, filters
from app.api.permissions import IsAdminUser
from app.api.response import Response
from flask_babel import gettext as _
from core.models import get_user_model
from user.admin import serializers


class AdminUserViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.AdminUserListSerializer
    permission_classes = [IsAdminUser]
    model = get_user_model()
    filter_backends = [filters.SearchFilter, filters.FieldFilterBackend]
    search_fields = ['email', 'name', 'surname']
    filterset_fields = ['is_active', 'is_staff', "is_ban"]
    http_method_names = ['get', 'patch', 'delete']

    def get_base_queryset(self):
        User = get_user_model()
        return User.query.order_by(User.created_at.desc())

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return serializers.AdminUserDetailSerializer
        if self.action in ['update', 'partial_update']:
            return serializers.AdminUserActionSerializer
        return self.serializer_class

    def get_object(self):
        id = self.kwargs.get('pk')
        User = get_user_model()
        return User.query.filter_by(id=id).one()

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        if user == request.user:
            return Response(
                {"error": _('you_cannot_delete_your_own_account')},
                status=status.HTTP_400_BAD_REQUEST
            )
        user.is_delete = True
        user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def partial_update(self, request, *args, **kwargs):
        user = self.get_object()
        if user == request.user:
            return Response(
                {"error": _('you_cannot_modify_your_own_account')},
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().partial_update(request, *args, **kwargs)
