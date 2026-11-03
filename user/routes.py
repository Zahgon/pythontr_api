"""The public account routes.

Three things here are preserved rather than repaired.

* Account creation queues its welcome mail and RETURNS a 500 document when the send
  fails -- from a hook whose return value is discarded, so the caller still gets the 201.
* A reset request for an unknown address is reported by a FIELD check that raises a
  mapping, so the body nests one level: ``{"email": {"error": "email_not_found"}}``. The
  confirmation's non-field check raises a mapping too and does not nest.
* ``GET /api/user/reset-password/confirm/`` (the registration with no arguments) calls a
  handler that requires two, so it raises.
"""

from smtplib import SMTPException

from sqlalchemy import select

from app import mail, views
from app.parsing import Field, parse_body, unique_error, validate
from app.security import (default_token_generator, urlsafe_base64_decode,
                          urlsafe_base64_encode)
from app.views import ALLOW_ANY, IS_AUTHENTICATED, View
from app.wire import ValidationFailed
from core.models import ActivationCode, Token, User, create_user, normalize_email

PUBLIC = {'GET': ALLOW_ANY, 'HEAD': ALLOW_ANY, 'POST': ALLOW_ANY,
          'OPTIONS': ALLOW_ANY}

USER_FIELDS = (
    Field('email', kind='email'),
    Field('password', min_length=5, write_only=True),
    Field('confirm_password', required=False, write_only=True),
    Field('username'),
    Field('name', required=False),
    Field('surname', required=False),
    Field('image', required=False, allow_null=True),
    Field('about_me', required=False),
    Field('linkedin', required=False),
    Field('github', required=False),
    Field('is_notification_email', required=False, kind='boolean'),
    Field('image_url', read_only=True),
    Field('slug', read_only=True),
    Field('is_staff', required=False, kind='boolean'),
    Field('current_password', required=False, write_only=True),
)

PUBLISHED_KEYS = ('email', 'username', 'name', 'surname', 'image', 'about_me',
                  'linkedin', 'github', 'is_notification_email', 'image_url', 'slug',
                  'is_staff')


def serialize_user(user):
    return {
        'email': user.email,
        'username': user.username,
        'name': user.name,
        'surname': user.surname,
        'image': user.image,
        'about_me': user.about_me,
        'linkedin': user.linkedin,
        'github': user.github,
        'is_notification_email': user.is_notification_email,
        'image_url': user.image_url,
        'slug': user.slug,
        'is_staff': user.is_staff,
    }


def _check_password_pair(data, method, current_user=None):
    password = data.get('password')
    if not password:
        return
    confirm_password = data.get('confirm_password')
    current_password = data.get('current_password')
    if not confirm_password:
        raise ValidationFailed({'confirm_password': ['please_confirm_your_password']})
    if password != confirm_password:
        raise ValidationFailed({'confirm_password': ['passwords_do_not_match']})
    if method in ('PUT', 'PATCH'):
        if not current_password:
            raise ValidationFailed(
                {'current_password': ['please_enter_your_current_password']})
        if not current_user.check_password(current_password):
            raise ValidationFailed(
                {'current_password': ['current_password_is_incorrect']})


class CreateUser(View):
    allow = 'POST, OPTIONS'
    permissions = PUBLIC
    title = 'Create User'

    async def post(self, request, session, user):
        payload = await parse_body(request)
        data = validate(payload, USER_FIELDS)
        _check_password_pair(data, request.method)
        if session.scalar(select(User.id).where(User.email == normalize_email(
                data['email']))):
            raise ValidationFailed(unique_error('email', 'user'))
        if session.scalar(select(User.id).where(User.username == data['username'])):
            raise ValidationFailed(unique_error('username', 'user'))
        password = data.pop('password')
        data.pop('confirm_password', None)
        data.pop('current_password', None)
        # A payload asking for staff is ignored.
        data['is_staff'] = False
        created = create_user(session, password=password, **data)
        self.perform_create(session, created)
        return serialize_user(created), 201, {}

    def perform_create(self, session, created):
        """The welcome mail. The 500 document this returns is DISCARDED by the caller."""
        from app import settings
        activation = ActivationCode.create_activation_code(session, created)
        try:
            mail.send_mail(
                _text('welcome_to_www'),
                _text('welcome_to_www_message').format(
                    link=f'{settings.SITE_URL}/register/activate/{activation.code}',
                    expires_at=activation.expires_at.strftime('%d/%m/%Y %H:%M')),
                settings.DEFAULT_FROM_EMAIL,
                [created.email],
                fail_silently=False,
            )
        except SMTPException as exc:
            return {'error': _text('error_sending_email'), 'detail': str(exc)}, 500, {}


def _text(key):
    from app.i18n import gettext
    return gettext(key)


class CreateToken(View):
    allow = 'POST, OPTIONS'
    permissions = PUBLIC
    title = 'Obtain Auth Token'

    FIELDS = (Field('email'), Field('password'))

    async def post(self, request, session, user):
        payload = await parse_body(request)
        data = validate(payload, self.FIELDS)
        account = session.scalar(select(User).where(User.email == data['email']))
        if (account is None or not account.is_active
                or not account.check_password(data['password'])):
            raise ValidationFailed({'non_field_errors': [
                'unable_to_authenticate_with_provided_credentials']})
        token = session.scalar(select(Token).where(Token.user_id == account.id))
        if token is None:
            token = Token(key=Token.generate_key(), user_id=account.id)
            session.add(token)
            session.flush()
        return {'token': token.key}, 200, {}


class ManageUser(View):
    allow = 'GET, PUT, PATCH, HEAD, OPTIONS'
    authenticators = views.TOKEN_FIRST_AUTHENTICATORS
    default_permission = IS_AUTHENTICATED
    title = 'Manage User'

    async def get(self, request, session, user):
        return serialize_user(user), 200, {}

    async def put(self, request, session, user):
        return await self._write(request, session, user, partial=False)

    async def patch(self, request, session, user):
        return await self._write(request, session, user, partial=True)

    async def _write(self, request, session, user, partial):
        payload = await parse_body(request)
        data = validate(payload, USER_FIELDS, partial=partial)
        _check_password_pair(data, request.method, user)
        if 'is_staff' in data and data['is_staff'] != user.is_staff and not user.is_staff:
            raise ValidationFailed(
                {'is_staff': ['only_staff_can_modify_staff_status']})
        password = data.pop('password', None)
        data.pop('confirm_password', None)
        data.pop('current_password', None)
        for key, value in data.items():
            setattr(user, key, value)
        if password:
            user.set_password(password)
        user.save(session)
        return serialize_user(user), 200, {}


class ActivateUser(View):
    allow = 'GET, HEAD, OPTIONS'
    permissions = PUBLIC
    title = 'Activate User'

    async def get(self, request, session, user):
        code = request.path_params['code']
        activation = session.scalar(select(ActivationCode).where(
            ActivationCode.code == code, ActivationCode.is_used.is_(False)))
        if activation is None:
            return {'error': _text('activation_code_is_invalid')}, 400, {}
        if activation.is_expired:
            return {'error': _text('activation_code_is_expired')}, 400, {}
        account = activation.user
        account.is_active = True
        account.save(session)
        activation.is_used = True
        session.add(activation)
        session.flush()
        return {'message': _text('account_activated_successfully')}, 200, {}


class ResendActivation(View):
    allow = 'POST, OPTIONS'
    permissions = PUBLIC
    title = 'Resend Activation'

    FIELDS = (Field('email', kind='email'),)

    async def post(self, request, session, user):
        from app import settings
        payload = await parse_body(request)
        data = validate(payload, self.FIELDS)
        account = session.scalar(select(User).where(
            User.email == data['email'], User.is_active.is_(False)))
        if account is None:
            return {'error': _text('user_not_found_with_active_code')}, 400, {}
        activation = ActivationCode.create_activation_code(session, account)
        try:
            mail.send_mail(
                _text('new_activation_code_title'),
                _text('new_activation_code_message').format(
                    link=f'{settings.SITE_URL}/register/activate/{activation.code}',
                    expires_at=activation.expires_at.strftime('%d/%m/%Y %H:%M')),
                settings.DEFAULT_FROM_EMAIL, [account.email], fail_silently=False)
        except SMTPException as exc:
            return {'error': _text('error_sending_email'), 'detail': str(exc)}, 500, {}
        return {'message': _text('new_activation_code_sent')}, 200, {}


class PasswordReset(View):
    allow = 'POST, OPTIONS'
    permissions = PUBLIC
    title = 'Password Reset'

    FIELDS = (Field('email', kind='email'),)

    async def post(self, request, session, user):
        from app import settings
        payload = await parse_body(request)
        data = validate(payload, self.FIELDS)
        account = session.scalar(select(User).where(User.email == data['email']))
        if account is None:
            # A FIELD check raising a mapping, so the body nests one level.
            raise ValidationFailed({'email': {'error': _text('email_not_found')}})
        token = default_token_generator.make_token(account)
        uidb64 = urlsafe_base64_encode(str(account.pk))
        try:
            reset_url = f'{settings.SITE_URL}/forgot-password/{uidb64}/{token}'
            mail.send_mail(_text('password_reset_title'),
                           _text('password_reset_message').format(link=reset_url),
                           settings.DEFAULT_FROM_EMAIL, [data['email']],
                           fail_silently=False)
        except SMTPException as exc:
            return {'error': _text('error_sending_email'), 'detail': str(exc)}, 500, {}
        return {'message': _text('password_reset_success_message_link_sent')}, 200, {}


class PasswordResetConfirm(View):
    """Registered twice: with ``uidb64`` and ``token``, and with neither."""

    allow = 'GET, POST, HEAD, OPTIONS'
    permissions = PUBLIC
    title = 'Password Reset Confirm'

    FIELDS = (Field('password', min_length=8, write_only=True),
              Field('confirm_password', write_only=True),
              Field('token'),
              Field('uidb64'))

    @staticmethod
    def _account(session, uidb64):
        """The account the encoded id names, or ``None`` if it names nothing."""
        try:
            uid = urlsafe_base64_decode(uidb64).decode('utf-8')
            return session.get(User, int(uid))
        except (TypeError, ValueError, UnicodeDecodeError):
            return None

    async def get(self, request, session, user):
        # The no-argument registration reaches here with nothing to read, and raises.
        uidb64 = request.path_params['uidb64']
        token = request.path_params['token']
        account = self._account(session, uidb64)
        if account is None:
            return {'error': _text('invalid_link')}, 400, {}
        if not default_token_generator.check_token(account, token):
            return {'error': _text('invalid_token_or_expired')}, 400, {}
        return {'valid': True}, 200, {}

    async def post(self, request, session, user):
        payload = await parse_body(request)
        data = validate(payload, self.FIELDS)
        if data['password'] != data['confirm_password']:
            raise ValidationFailed({'confirm_password': ['passwords_do_not_match']})
        account = self._account(session, data['uidb64'])
        if account is None:
            raise ValidationFailed({'error': ['invalid_link']})
        if not default_token_generator.check_token(account, data['token']):
            raise ValidationFailed({'error': ['invalid_link_or_expired']})
        account.set_password(data['password'])
        account.save(session)
        return {'message': _text('password_reset_success_message')}, 200, {}
