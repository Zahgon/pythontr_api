import requests

from flask import current_app
from flask_babel import gettext as _

from marshmallow import ValidationError, validates
from sqlalchemy.orm.exc import NoResultFound

from app import settings
from app.api import fields, messages
from app.api.serializers import Serializer
from app.api.validators import unique_check

from core.auth import authenticate
from core.tokens import default_token_generator, force_str, \
    urlsafe_base64_decode
from core.models import User


class UserSerializer(Serializer):
    email = fields.EmailField(required=True, max_length=255)
    password = fields.CharField(
        required=True,
        load_only=True,
        min_length=5,
        max_length=128,
        metadata={'label': messages.Message('Parola', 'Password')},
    )
    confirm_password = fields.CharField(
        load_only=True,
        required=False,
    )
    username = fields.CharField(required=True, max_length=255)
    name = fields.CharField(required=False, allow_blank=True, max_length=255)
    surname = fields.CharField(
        required=False, allow_blank=True, max_length=255
    )
    image = fields.ImageField(required=False, allow_none=True)
    about_me = fields.CharField(required=False, allow_blank=True)
    linkedin = fields.CharField(
        required=False, allow_blank=True, max_length=255)
    github = fields.CharField(required=False, allow_blank=True, max_length=255)
    is_notification_email = fields.BooleanField(required=False)
    image_url = fields.ReadOnlyField()
    slug = fields.SlugField(dump_only=True)
    is_staff = fields.BooleanField(required=False)
    current_password = fields.CharField(
        load_only=True,
        required=False,
    )
    if settings.CAPTCHA_REQUIRED:
        captcha = fields.CharField(load_only=True, required=True)

        @validates('captcha')
        def validate_captcha(self, value):
            recaptcha_url = current_app.config['RECAPTCHA_URL']
            payload = {
                "secret": current_app.config['RECAPTCHA_SECRET_KEY'],
                "response": value
            }
            response = requests.post(recaptcha_url, data=payload)
            result = response.json()

            if not result.get("success"):
                raise ValidationError(
                    _("recaptcha_verification_failed"))

            return value

    @validates('email')
    def validate_email_unique(self, value):
        unique_check(User, User.email, value, self.instance,
                     field='email', label='user')

    @validates('username')
    def validate_username_unique(self, value):
        unique_check(User, User.username, value, self.instance,
                     field='username', label='user')

    def validate(self, data):
        password = data.get('password')
        if password:
            confirm_password = data.get('confirm_password')
            current_password = data.get('current_password')

            if not confirm_password:
                raise ValidationError({
                    'confirm_password': [_('please_confirm_your_password')]
                })

            if password != confirm_password:
                raise ValidationError({
                    "confirm_password": [_("passwords_do_not_match")]
                    })

            if self.context['request'].method in ['PUT', 'PATCH']:
                if not current_password:
                    raise ValidationError({
                        'current_password': [_(
                            'please_enter_your_current_password'
                        )]
                    })

                user = self.context['request'].user
                if not user.check_password(current_password):
                    raise ValidationError({
                        'current_password': [
                            _('current_password_is_incorrect')
                        ]
                    })

        return data

    @validates('is_staff')
    def validate_is_staff(self, value):
        request = self.context.get('request')
        if self.instance and request.method in ['PUT', 'PATCH']:
            if value != self.instance.is_staff and not request.user.is_staff:
                raise ValidationError(
                    _('only_staff_can_modify_staff_status'))
        return value

    def create(self, validated_data):
        validated_data['is_staff'] = False
        password = validated_data.pop('password')
        validated_data.pop('confirm_password')
        if settings.CAPTCHA_REQUIRED:
            validated_data.pop('captcha')
        return User.objects.create_user(
            password=password,
            **validated_data
        )

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        if self.partial:
            validated_data.pop('confirm_password', None)
            validated_data.pop('current_password', None)
        else:
            validated_data.pop('confirm_password')
            validated_data.pop('current_password')
        if password:
            instance.set_password(password)
        return super().update(instance, validated_data)


class AuthTokenSerializer(Serializer):
    """Serializer for the user authentication object"""
    email = fields.CharField(required=True)
    password = fields.CharField(
        required=True,
        trim_whitespace=False
    )

    if settings.CAPTCHA_REQUIRED:
        captcha = fields.CharField(load_only=True, required=True)

        @validates('captcha')
        def validate_captcha(self, value):
            recaptcha_url = current_app.config['RECAPTCHA_URL']
            payload = {
                "secret": current_app.config['RECAPTCHA_SECRET_KEY'],
                "response": value
            }
            response = requests.post(recaptcha_url, data=payload)
            result = response.json()

            if not result.get("success"):
                raise ValidationError(
                    _("recaptcha_verification_failed"))

            return value

    def validate(self, attrs):
        """Validate and authenticate the user"""
        email = attrs.get('email')
        password = attrs.get('password')

        user = authenticate(
            request=self.context.get('request'),
            username=email,
            password=password
        )
        if not user:
            msg = _('unable_to_authenticate_with_provided_credentials')
            raise ValidationError({'non_field_errors': [msg]})

        attrs['user'] = user
        return attrs


class PasswordResetSerializer(Serializer):
    email = fields.EmailField(required=True)

    if settings.CAPTCHA_REQUIRED:
        captcha = fields.CharField(load_only=True, required=True)

        @validates('captcha')
        def validate_captcha(self, value):
            recaptcha_url = current_app.config['RECAPTCHA_URL']
            payload = {
                "secret": current_app.config['RECAPTCHA_SECRET_KEY'],
                "response": value
            }
            response = requests.post(recaptcha_url, data=payload)
            result = response.json()
            if not result.get("success"):
                raise ValidationError(
                    _("recaptcha_verification_failed"))
            return value

    @validates('email')
    def validate_email(self, value):
        try:
            User.query.filter_by(email=value).one()
        except NoResultFound:
            raise ValidationError({"error": _('email_not_found')})
        return value


class PasswordResetConfirmSerializer(Serializer):
    password = fields.CharField(
        required=True,
        load_only=True,
        min_length=8,
    )
    confirm_password = fields.CharField(
        required=True,
        load_only=True,
    )
    token = fields.CharField(required=True)
    uidb64 = fields.CharField(required=True)

    if settings.CAPTCHA_REQUIRED:
        captcha = fields.CharField(load_only=True, required=True)

        @validates('captcha')
        def validate_captcha(self, value):
            recaptcha_url = current_app.config['RECAPTCHA_URL']
            payload = {
                "secret": current_app.config['RECAPTCHA_SECRET_KEY'],
                "response": value
            }
            response = requests.post(recaptcha_url, data=payload)
            result = response.json()
            if not result.get("success"):
                raise ValidationError(
                    _("recaptcha_verification_failed"))
            return value

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise ValidationError(
                {'confirm_password': [_('passwords_do_not_match')]}
            )
        try:
            uid = force_str(urlsafe_base64_decode(data['uidb64']))
            user = User.query.filter_by(id=int(uid)).one()
        except (TypeError, ValueError, NoResultFound):
            raise ValidationError({'error': [_('invalid_link')]})

        if not default_token_generator.check_token(user, data['token']):
            raise ValidationError(
                {'error': [_('invalid_link_or_expired')]})

        data['user'] = user
        return data


class ResendActivationSerializer(Serializer):
    email = fields.EmailField(required=True)

    if settings.CAPTCHA_REQUIRED:
        captcha = fields.CharField(load_only=True, required=True)

        @validates('captcha')
        def validate_captcha(self, value):
            recaptcha_url = current_app.config['RECAPTCHA_URL']
            payload = {
                "secret": current_app.config['RECAPTCHA_SECRET_KEY'],
                "response": value
            }
            response = requests.post(recaptcha_url, data=payload)
            result = response.json()

            if not result.get("success"):
                raise ValidationError(
                    _("recaptcha_verification_failed"))

            return value
