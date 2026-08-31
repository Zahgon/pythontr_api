from marshmallow import validates

from app.api import fields
from app.api.serializers import Serializer
from app.api.validators import unique_check
from core.models import Article, Category, User


class ArticleListSerializer(Serializer):
    """Serializer for article list"""

    id = fields.IntegerField(dump_only=True)
    title = fields.CharField(required=True, max_length=255)
    title_h1 = fields.CharField(required=True, max_length=255)
    description = fields.CharField(required=False, allow_blank=True)
    image = fields.ImageField(required=False, allow_none=True)
    read_count = fields.IntegerField(dump_only=True)
    image_url = fields.ReadOnlyField()
    slug = fields.CharField(dump_only=True)
    categories = fields.PrimaryKeyRelatedField(
        Category, many=True, required=True
    )
    user = fields.PrimaryKeyRelatedField(
        User, required=False, allow_none=True
    )
    username = fields.CharField(attribute='user.username', dump_only=True)
    is_active = fields.BooleanField(dump_only=True)
    is_approval = fields.BooleanField(required=False)
    created_at = fields.DateTimeField(dump_only=True)
    updated_at = fields.DateTimeField(dump_only=True)

    @validates('title')
    def validate_title(self, value):
        unique_check(Article, Article.title, value, self.instance,
                     field='title', label='article')

    def create(self, validated_data):
        return Article(**validated_data).save()
