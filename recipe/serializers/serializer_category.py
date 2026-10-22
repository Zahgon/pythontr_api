from marshmallow import validates

from app.api import fields
from app.api.serializers import Serializer
from app.api.validators import unique_check
from core.models import Category


class CategoryReleatedSerializer(Serializer):
    """Serializer for category"""

    id = fields.IntegerField(dump_only=True)
    parent_category = fields.PrimaryKeyRelatedField(
        Category, required=False, allow_none=True
    )
    name = fields.CharField(required=True, max_length=255)
    title = fields.CharField(required=True, max_length=255)
    title_h1 = fields.CharField(required=True, max_length=255)
    description = fields.CharField(
        required=False, allow_none=True, allow_blank=True
    )
    content = fields.CharField(
        required=False, allow_none=True, allow_blank=True
    )
    slug = fields.SlugField(dump_only=True)
    short_name = fields.CharField(required=True, max_length=100)
    full_category_name = fields.ReadOnlyField()
    created_at = fields.DateTimeField(dump_only=True)
    updated_at = fields.DateTimeField(dump_only=True)

    @validates('name')
    def validate_name(self, value):
        unique_check(Category, Category.name, value, self.instance,
                     field='name', label='category')

    @validates('title')
    def validate_title(self, value):
        unique_check(Category, Category.title, value, self.instance,
                     field='title', label='category')

    @validates('short_name')
    def validate_short_name(self, value):
        unique_check(Category, Category.short_name, value, self.instance,
                     field='short name', label='category')

    def create(self, validated_data):
        return Category(**validated_data).save()


class CategorySerializer(CategoryReleatedSerializer):
    """Serializer for category with the categories directly below it"""

    categories = fields.NestedField(
        CategoryReleatedSerializer, many=True, attribute='category_set'
    )
