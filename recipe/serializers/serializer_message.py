from app.api import fields
from app.api.serializers import Serializer
from core.models import Message, User


class MessageSerializer(Serializer):
    """Serializer for message"""

    id = fields.IntegerField(dump_only=True)
    created_at = fields.DateTimeField(dump_only=True)
    sender = fields.PrimaryKeyRelatedField(
        User, required=False, allow_none=True
    )
    user = fields.PrimaryKeyRelatedField(
        User, required=False, allow_none=True
    )
    subject = fields.CharField(required=True, max_length=255)
    content = fields.CharField(required=True)
    ip = fields.CharField(required=True, max_length=100)
    is_read = fields.BooleanField(required=False)
    is_delete = fields.BooleanField(required=False)

    def create(self, validated_data):
        return Message(**validated_data).save()
