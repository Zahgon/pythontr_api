from app.api import fields
from app.api.serializers import Serializer
from core.models import get_user_model


class AdminUserListSerializer(Serializer):
    id = fields.IntegerField(dump_only=True)
    username = fields.CharField(required=True, max_length=255)
    email = fields.EmailField(dump_only=True)
    name = fields.CharField(dump_only=True)
    surname = fields.CharField(required=False, allow_blank=True,
                               max_length=255)
    image = fields.ImageField(required=False, allow_none=True)
    is_active = fields.BooleanField(required=False)
    is_staff = fields.BooleanField(required=False)
    is_ban = fields.BooleanField(required=False)
    is_delete = fields.BooleanField(required=False)
    created_at = fields.DateTimeField(dump_only=True)
    updated_at = fields.DateTimeField(dump_only=True)

    model = get_user_model()


class AdminUserDetailSerializer(Serializer):
    id = fields.IntegerField(dump_only=True)
    username = fields.CharField(required=True, max_length=255)
    email = fields.EmailField(dump_only=True)
    name = fields.CharField(dump_only=True)
    surname = fields.CharField(dump_only=True)
    image = fields.ImageField(required=False, allow_none=True)
    about_me = fields.CharField(dump_only=True)
    is_active = fields.BooleanField(required=False)
    is_staff = fields.BooleanField(required=False)
    is_ban = fields.BooleanField(required=False)
    is_delete = fields.BooleanField(required=False)
    created_at = fields.DateTimeField(dump_only=True)
    # ``updated_at`` is stamped by the model on every write, so it was never
    # settable through the API even though it is absent from read_only_fields.
    updated_at = fields.DateTimeField(dump_only=True)

    model = get_user_model()


class AdminUserActionSerializer(Serializer):
    is_active = fields.BooleanField(required=False)
    is_staff = fields.BooleanField(required=False)
    is_ban = fields.BooleanField(required=False)
    is_delete = fields.BooleanField(required=False)

    model = get_user_model()
