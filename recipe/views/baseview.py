from app.api import views, mixins
from app.api.permissions import IsAuthenticated, AllowAny, IsAdminUser
from app.authentication import CookieTokenAuthentication, TokenAuthentication


class BaseViewSet(views.GenericViewSet,
                  mixins.ListModelMixin,
                  mixins.RetrieveModelMixin,
                  mixins.UpdateModelMixin,
                  # mixins.DestroyModelMixin
                  ):

    authentication_classes = (TokenAuthentication, CookieTokenAuthentication)
    permission_classes = (IsAuthenticated,)

    permission_classes_by_action = {'update': [IsAdminUser],
                                    'retrieve': [AllowAny],
                                    'list': [AllowAny]}

    def get_permissions(self):
        try:
            result = None
            permission_list = []
            for permission in self.permission_classes_by_action[self.action]:
                permission_list.append(permission())
            result = permission_list
        except KeyError:
            result = [permission() for permission in self.permission_classes]
        finally:
            return result

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
