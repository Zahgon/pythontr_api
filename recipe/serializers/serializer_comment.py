import requests
from flask import current_app
from flask_babel import gettext as _
from marshmallow import ValidationError, validates

from app import settings
from app.api import fields
from app.api.serializers import Serializer
from core.models import Comment, ContentType, User


class CommentSerializer(Serializer):
    """Serializer for comment"""

    id = fields.IntegerField(dump_only=True)
    content = fields.CharField(required=False, allow_blank=True)
    email = fields.CharField(required=True, max_length=100)
    name = fields.CharField(required=True, max_length=50)
    ip = fields.CharField(required=True, max_length=100)
    user = fields.PrimaryKeyRelatedField(
        User, required=False, allow_none=True
    )
    content_type = fields.PrimaryKeyRelatedField(ContentType, required=True)
    object_id = fields.IntegerField(required=True)
    comments = fields.SerializerMethodField()

    if settings.CAPTCHA_REQUIRED:
        captcha = fields.CharField(required=True, load_only=True)

        @validates('captcha')
        def validate_captcha(self, value):
            response = requests.post(
                current_app.config['RECAPTCHA_URL'],
                data={
                    "secret": current_app.config['RECAPTCHA_SECRET_KEY'],
                    "response": value,
                },
            )
            result = response.json()
            if not result.get("success"):
                raise ValidationError(_("recaptcha_verification_failed"))

    def get_comments(self, obj):
        content_type = ContentType.get_for_model(Comment)
        replies = Comment.query.filter(
            Comment.content_type_id == content_type.id,
            Comment.object_id == obj.id,
        )
        return CommentSerializer(context=self.context, many=True).dump(replies)

    def create(self, validated_data):
        return Comment(**validated_data).save()
