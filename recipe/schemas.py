"""Serialisation for the recipe collections. Key order is the published order."""

from app.parsing import Field
from app.wire import stamp as _stamp
from sqlalchemy import select


CATEGORY_RELATED_KEYS = ('id', 'parent_category', 'name', 'title', 'title_h1',
                         'description', 'content', 'slug', 'short_name',
                         'full_category_name', 'created_at', 'updated_at')


def serialize_category_related(category):
    return {
        'id': category.id,
        'parent_category': category.parent_category_id,
        'name': category.name,
        'title': category.title,
        'title_h1': category.title_h1,
        'description': category.description,
        'content': category.content,
        'slug': category.slug,
        'short_name': category.short_name,
        'full_category_name': category.full_category_name,
        'created_at': _stamp(category.created_at),
        'updated_at': _stamp(category.updated_at),
    }


def serialize_category(category):
    """A category with its direct children under ``categories``."""
    payload = serialize_category_related(category)
    payload['categories'] = [serialize_category_related(child)
                             for child in category.categories]
    return payload


CATEGORY_FIELDS = (
    Field('id', read_only=True),
    Field('parent_category', required=False, allow_null=True, kind='integer'),
    Field('name'),
    Field('title'),
    Field('title_h1', required=False),
    Field('description', required=False, allow_null=True),
    Field('content', required=False, allow_null=True),
    Field('slug', read_only=True),
    Field('short_name'),
    Field('full_category_name', read_only=True),
    Field('created_at', read_only=True),
    Field('updated_at', read_only=True),
)


def serialize_comment(comment, session):
    """A comment and, under ``comments``, every comment whose parent is this one."""
    from core.models import Comment
    children = session.scalars(
        select(Comment).where(Comment.content_type_id == 11,
                              Comment.object_id == comment.id)
        .order_by(Comment.id)).all()
    return {
        'id': comment.id,
        'content': comment.content,
        'email': comment.email,
        'name': comment.name,
        'ip': comment.ip,
        'user': comment.user_id,
        'content_type': comment.content_type_id,
        'object_id': comment.object_id,
        'comments': [serialize_comment(child, session) for child in children],
    }


COMMENT_FIELDS = (
    Field('id', read_only=True),
    Field('content', required=False),
    Field('email'),
    Field('name'),
    Field('ip'),
    Field('user', required=False, allow_null=True, kind='integer'),
    Field('content_type', kind='integer'),
    Field('object_id', kind='integer'),
    Field('comments', read_only=True),
)


def serialize_article(article, session):
    return {
        'id': article.id,
        'categories': [category.id for category in article.categories],
        'title': article.title,
        'title_h1': article.title_h1,
        'description': article.description,
        'content': article.content,
        'image': article.image,
        'read_count': article.read_count,
        'image_url': article.image_url,
        'slug': article.slug,
        'user': article.user_id,
        'username': article.user.username if article.user else None,
        'is_active': article.is_active,
        'is_approval': article.is_approval,
        'approval_user': article.approval_user_id,
        'is_delete': article.is_delete,
        'comments': [serialize_comment(comment, session)
                     for comment in _article_comments(article, session)],
        'created_at': _stamp(article.created_at),
        'updated_at': _stamp(article.updated_at),
    }


def _article_comments(article, session):
    from core.models import Comment
    return session.scalars(
        select(Comment).where(Comment.content_type_id == 10,
                              Comment.object_id == article.id)
        .order_by(Comment.id)).all()


def serialize_article_list(article):
    """The list document, which drops ``content``, ``approval_user`` and the comments."""
    return {
        'id': article.id,
        'title': article.title,
        'title_h1': article.title_h1,
        'description': article.description,
        'image': article.image,
        'read_count': article.read_count,
        'image_url': article.image_url,
        'slug': article.slug,
        'categories': [category.id for category in article.categories],
        'user': article.user_id,
        'username': article.user.username if article.user else None,
        'is_active': article.is_active,
        'is_approval': article.is_approval,
        'created_at': _stamp(article.created_at),
        'updated_at': _stamp(article.updated_at),
    }


ARTICLE_FIELDS = (
    Field('id', read_only=True),
    Field('categories', kind='integer_list'),
    Field('title'),
    Field('title_h1', required=False),
    Field('description', required=False),
    Field('content', required=False),
    Field('image', required=False, allow_null=True),
    Field('read_count', read_only=True),
    Field('image_url', read_only=True),
    Field('slug', read_only=True),
    Field('user', required=False, allow_null=True, kind='integer'),
    Field('username', read_only=True),
    Field('is_active', required=False, kind='boolean'),
    Field('is_approval', required=False, kind='boolean'),
    Field('approval_user', required=False, allow_null=True, kind='integer'),
    Field('is_delete', required=False, kind='boolean'),
    Field('comments', read_only=True),
    Field('created_at', read_only=True),
    Field('updated_at', read_only=True),
)


def serialize_slider(slider):
    return {
        'id': slider.id,
        'title': slider.title,
        'description': slider.description,
        'link': slider.link,
        'image': slider.image,
        'image_url': slider.image_url,
        'user': slider.user_id,
        'username': slider.user.username if slider.user else None,
        'is_active': slider.is_active,
        'is_approval': slider.is_approval,
        'approval_user': slider.approval_user_id,
        'is_delete': slider.is_delete,
        'created_at': _stamp(slider.created_at),
        'updated_at': _stamp(slider.updated_at),
    }


SLIDER_FIELDS = (
    Field('id', read_only=True),
    Field('title'),
    Field('description', required=False, allow_null=True),
    Field('link', required=False, allow_null=True),
    Field('image', required=False, allow_null=True),
    Field('image_url', read_only=True),
    Field('user', required=False, allow_null=True, kind='integer'),
    Field('username', read_only=True),
    Field('is_active', read_only=True),
    Field('is_approval', required=False, kind='boolean'),
    Field('approval_user', required=False, allow_null=True, kind='integer'),
    Field('is_delete', read_only=True),
    Field('created_at', read_only=True),
    Field('updated_at', read_only=True),
)


def serialize_message(message):
    return {
        'id': message.id,
        'created_at': _stamp(message.created_at),
        'sender': message.sender_id,
        'user': message.user_id,
        'subject': message.subject,
        'content': message.content,
        'ip': message.ip,
        'is_read': message.is_read,
        'is_delete': message.is_delete,
    }


MESSAGE_FIELDS = (
    Field('id', read_only=True),
    Field('created_at', required=False),
    Field('sender', required=False, allow_null=True, kind='integer'),
    Field('user', required=False, allow_null=True, kind='integer'),
    Field('subject'),
    Field('content'),
    Field('ip'),
    Field('is_read', required=False, kind='boolean'),
    Field('is_delete', required=False, kind='boolean'),
)
