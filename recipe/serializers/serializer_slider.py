from marshmallow import validates

from app.api import fields
from app.api.serializers import Serializer
from app.api.validators import unique_check
from core.models import Slider, User


class SliderSerializer(Serializer):
    """Serializer for slider"""

    id = fields.IntegerField(dump_only=True)
    title = fields.CharField(required=True, max_length=255)
    description = fields.CharField(
        required=False, allow_none=True, allow_blank=True
    )
    link = fields.CharField(
        required=False, allow_none=True, allow_blank=True, max_length=255
    )
    image = fields.ImageField(required=False, allow_none=True)
    image_url = fields.ReadOnlyField()
    user = fields.PrimaryKeyRelatedField(
        User, required=False, allow_none=True
    )
    username = fields.CharField(attribute='user.username', dump_only=True)
    is_active = fields.BooleanField(dump_only=True)
    is_approval = fields.BooleanField(required=False)
    approval_user = fields.PrimaryKeyRelatedField(
        User, required=False, allow_none=True
    )
    is_delete = fields.BooleanField(dump_only=True)
    created_at = fields.DateTimeField(dump_only=True)
    updated_at = fields.DateTimeField(dump_only=True)

    @validates('title')
    def validate_title(self, value):
        unique_check(Slider, Slider.title, value, self.instance,
                     field='title', label='slider')

    def create(self, validated_data):
        return Slider(**validated_data).save()
