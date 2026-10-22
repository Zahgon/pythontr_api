import base64

from marshmallow import ValidationError, validates

from app.api import fields
from app.api.serializers import Serializer
from app.api.validators import unique_check
from core.models import Article, Category, User
from core.storage import ContentFile
from core.text import slugify
from recipe.serializers.serializer_comment import CommentSerializer


class ArticleSerializer(Serializer):
    """Serializer for article"""

    id = fields.IntegerField(dump_only=True)
    categories = fields.PrimaryKeyRelatedField(
        Category, many=True, required=True
    )
    title = fields.CharField(required=True, max_length=255)
    title_h1 = fields.CharField(required=True, max_length=255)
    description = fields.CharField(required=False, allow_blank=True)
    content = fields.CharField(required=False, allow_blank=True)
    image = fields.ImageField(required=False, allow_none=True)
    read_count = fields.IntegerField(dump_only=True)
    image_url = fields.ReadOnlyField()
    slug = fields.SlugField(dump_only=True)
    user = fields.PrimaryKeyRelatedField(
        User, required=False, allow_none=True
    )
    username = fields.CharField(attribute='user.username', dump_only=True)
    is_active = fields.BooleanField(required=False)
    is_approval = fields.BooleanField(required=False)
    approval_user = fields.PrimaryKeyRelatedField(
        User, required=False, allow_none=True
    )
    is_delete = fields.BooleanField(required=False)
    comments = fields.NestedField(CommentSerializer, many=True)
    created_at = fields.DateTimeField(dump_only=True)
    updated_at = fields.DateTimeField(dump_only=True)

    @validates('title')
    def validate_title(self, value):
        unique_check(Article, Article.title, value, self.instance,
                     field='title', label='article')

    def validate(self, data):
        request = self.context.get('request')
        if 'is_approval' in data:
            if not request.user.is_staff and data['is_approval'] is True:
                raise ValidationError({
                    "is_approval": [
                        "Onay durumunu sadece yöneticiler değiştirebilir."
                    ]
                })
            if data['is_approval'] is True:
                data['approval_user'] = request.user
            elif data['is_approval'] is False:
                data['approval_user'] = None
        return data

    def to_internal_value(self, data):
        if isinstance(data.get('image'), str) \
                and data['image'].startswith('data:image'):
            format, imgstr = data['image'].strip().split(';base64,')
            ext = format.split('/')[-1]
            filename = slugify(data['title'])[:50] if 'title' in data \
                else 'temp'
            data = data.copy()
            data['image'] = ContentFile(
                base64.b64decode(imgstr), name=f'{filename}.{ext}'
            )
        return data

    def create(self, validated_data):
        return Article(**validated_data).save()
