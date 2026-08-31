
from smtplib import SMTPException

from flask import current_app
from flask_babel import gettext as _
from sqlalchemy.orm.exc import NoResultFound

from app.api import views as generics, permissions
from app.api.authtoken import ObtainAuthToken
from app.api.response import Response
from app.api import status
from app.mail import send_mail

from app import authentication
from app.authentication import CookieTokenAuthentication
from core.tokens import default_token_generator, force_bytes, force_str, \
    urlsafe_base64_encode, urlsafe_base64_decode
from user.serializers import UserSerializer, AuthTokenSerializer, \
    PasswordResetSerializer, PasswordResetConfirmSerializer, \
    ResendActivationSerializer
from core.models import ActivationCode, User


class CreateUserView(generics.CreateAPIView):
    serializer_class = UserSerializer

    def perform_create(self, serializer):
        user = serializer.save()
        activation = ActivationCode.create_activation_code(user)
        try:
            send_mail(
                _('welcome_to_www'),
                _('welcome_to_www_message').format(
                    link=f'{current_app.config["SITE_URL"]}'
                         f'/register/activate/{activation.code}',
                    expires_at=activation.expires_at.strftime("%d/%m/%Y %H:%M")
                ),
                current_app.config['MAIL_DEFAULT_SENDER'],
                [user.email],
                fail_silently=False,
            )
        except SMTPException as e:
            return Response(
                {'error': _('error_sending_email'), 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CreateTokenView(ObtainAuthToken):
    serializer_class = AuthTokenSerializer


class ManageUserView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    authentication_classes = (authentication.TokenAuthentication,
                              CookieTokenAuthentication)
    permission_classes = (permissions.IsAuthenticated,)

    def get_object(self):
        return self.request.user

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class ActivateUserView(generics.GenericAPIView):
    def get(self, request, code):
        try:
            activation = ActivationCode.query.filter_by(
                code=str(code),
                is_used=False
            ).one()

            if activation.is_expired:
                return Response(
                    {'error': _('activation_code_is_expired')},
                    status=status.HTTP_400_BAD_REQUEST
                )

            user = activation.user
            user.is_active = True
            user.save()

            activation.is_used = True
            activation.save()

            return Response(
                {'message': _('account_activated_successfully')},
                status=status.HTTP_200_OK
            )

        except NoResultFound:
            return Response(
                {'error': _('activation_code_is_invalid')},
                status=status.HTTP_400_BAD_REQUEST
            )


class ResendActivationView(generics.GenericAPIView):
    serializer_class = ResendActivationSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']

        try:
            user = User.query.filter_by(email=email, is_active=False).one()
            activation = ActivationCode.create_activation_code(user)

            send_mail(
                _('new_activation_code_title'),
                _('new_activation_code_message').format(
                    link=f'{current_app.config["SITE_URL"]}'
                         f'/register/activate/{activation.code}',
                    expires_at=activation.expires_at.strftime("%d/%m/%Y %H:%M")
                ),
                current_app.config['MAIL_DEFAULT_SENDER'],
                [user.email],
                fail_silently=False,
            )

            return Response(
                {'message': _('new_activation_code_sent')},
                status=status.HTTP_200_OK
            )

        except NoResultFound:
            return Response(
                {'error': _('user_not_found_with_active_code')},
                status=status.HTTP_400_BAD_REQUEST
            )
        except SMTPException as e:
            return Response(
                {'error': _('error_sending_email'), 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PasswordResetView(generics.GenericAPIView):
    serializer_class = PasswordResetSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        user = User.query.filter_by(email=email).one()

        # Token and UID
        token = default_token_generator.make_token(user)
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))

        # Send Email
        try:
            site_url = current_app.config['SITE_URL']
            reset_url = f"{site_url}/forgot-password/{uidb64}/{token}"
            send_mail(
                _('password_reset_title'),
                _('password_reset_message').format(link=reset_url),
                current_app.config['MAIL_DEFAULT_SENDER'],
                [email],
                fail_silently=False,
            )
        except SMTPException as e:
            return Response(
                {'error': _('error_sending_email'), 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response({
            'message': _('password_reset_success_message_link_sent')
        })


class PasswordResetConfirmView(generics.GenericAPIView):
    serializer_class = PasswordResetConfirmSerializer

    def get(self, request, uidb64, token):
        try:
            # Check Token and UID
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.query.filter_by(id=int(uid)).one()

            if not default_token_generator.check_token(user, token):
                return Response(
                    {'error': _('invalid_token_or_expired')},
                    status=status.HTTP_400_BAD_REQUEST
                )

            return Response({'valid': True})

        except (TypeError, ValueError, NoResultFound):
            return Response(
                {'error': _('invalid_link')},
                status=status.HTTP_400_BAD_REQUEST
            )

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data['user']
        password = serializer.validated_data['password']

        user.set_password(password)
        user.save()

        return Response({
            'message': _('password_reset_success_message')
        })
