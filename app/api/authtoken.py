"""Token issuing endpoint.

The login endpoint is not written by hand in the original project either: it
subclasses the framework's ready-made view, so the same view lives here to keep
``user/views.py`` a two-line class.
"""
from app.api.response import Response
from app.api.views import APIView

from core.models import Token


class ObtainAuthToken(APIView):
    permission_classes = ()
    serializer_class = None

    def get_serializer_context(self):
        return {
            'request': self.request,
            'view': self,
        }

    def get_serializer(self, *args, **kwargs):
        kwargs['context'] = self.get_serializer_context()
        return self.serializer_class(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.get_or_create(user=user)
        return Response({'token': token.key})
