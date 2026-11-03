"""The five recipe collections.

Two things here are preserved rather than repaired, and both are observable.

* A detail route loads its row directly and never consults an object-level rule, so
  ownership is not enforced on an article, a category or a slider, and a row that is not
  there raises instead of answering 404.
* ``partial_update`` is absent from every permission map, so a ``PATCH`` falls through to
  the bare authenticated rule.
"""

from sqlalchemy import func, or_, select

from app import views
from app.parsing import parse_body, unique_error, validate
from app.views import (ALLOW_ANY, IS_ADMIN, IS_AUTHENTICATED,
                       IS_AUTHENTICATED_OR_READ_ONLY, View)
from app.wire import NotFound, PermissionDenied, ValidationFailed, paginate
from core.models import (Article, Category, Comment, Message, Slider,
                         article_categories, visible_messages)
from recipe import schemas
from recipe.filter_param import Category as CategoryRule
from recipe.filter_param import Inbox, Me, Outbox, RulesFilter, Search

COLLECTION_ALLOW = 'GET, POST, HEAD, OPTIONS'
DETAIL_ALLOW = 'GET, PUT, PATCH, HEAD, OPTIONS'
ARTICLE_DETAIL_ALLOW = 'GET, PUT, PATCH, DELETE, HEAD, OPTIONS'


class ApiRoot(View):
    allow = 'GET, HEAD, OPTIONS'
    permissions = {'GET': ALLOW_ANY, 'HEAD': ALLOW_ANY, 'OPTIONS': ALLOW_ANY}
    title = 'Api Root'

    async def get(self, request, session, user):
        base = str(request.base_url).rstrip('/')
        from app.urls import suffixed
        suffix = request.scope.get('format_suffix')
        names = ('categories', 'articles', 'sliders', 'comments', 'messages')
        return ({name: base + suffixed('/api/recipe/%s/' % name, suffix)
                 for name in names}, 200, {})


# --- categories -------------------------------------------------------------------

class CategoryCollection(View):
    allow = COLLECTION_ALLOW
    authenticators = views.TOKEN_FIRST_AUTHENTICATORS
    permissions = {'GET': IS_AUTHENTICATED_OR_READ_ONLY,
                   'HEAD': IS_AUTHENTICATED_OR_READ_ONLY, 'POST': IS_ADMIN}
    title = 'Category List'

    async def get(self, request, session, user):
        search = request.query_params.get('search')
        rules = [Search(search, **{'name__icontains': search})]
        kwargs = {}
        for rule in RulesFilter(rules).get_res():
            if rule.is_check():
                kwargs.update(rule.get_param())
        statement = select(Category)
        if 'name__icontains' in kwargs:
            statement = statement.where(
                func.lower(Category.name).contains(str(kwargs['name__icontains']).lower()))
        rows = session.scalars(statement).all()
        # Sorted in Python on the joined parent chain, which is what the old queryset did.
        rows = sorted(rows, key=lambda row: row.full_category_name)
        return paginate(request, rows, schemas.serialize_category), 200, {}

    async def post(self, request, session, user):
        payload = await parse_body(request)
        data = validate(payload, schemas.CATEGORY_FIELDS)
        if session.scalar(select(Category.id).where(Category.name == data['name'])):
            raise ValidationFailed(unique_error('name', 'category'))
        category = Category(**data)
        category.save(session)
        return schemas.serialize_category(category), 201, {}


class CategoryDetail(View):
    allow = DETAIL_ALLOW
    authenticators = views.TOKEN_FIRST_AUTHENTICATORS
    permissions = {'GET': IS_AUTHENTICATED_OR_READ_ONLY,
                   'HEAD': IS_AUTHENTICATED_OR_READ_ONLY}
    default_permission = IS_AUTHENTICATED
    title = 'Category Instance'

    def get_object(self, request, session):
        """Loads the row and nothing else: no object-level rule is consulted, and a row
        that is not there raises."""
        id_or_slug = request.path_params['pk']
        if id_or_slug.isdigit():
            return _one(session, Category, Category.id == int(id_or_slug))
        return _one(session, Category, Category.slug == id_or_slug)

    async def get(self, request, session, user):
        return schemas.serialize_category(self.get_object(request, session)), 200, {}

    async def put(self, request, session, user):
        return await self._write(request, session, partial=False)

    async def patch(self, request, session, user):
        return await self._write(request, session, partial=True)

    async def _write(self, request, session, partial):
        category = self.get_object(request, session)
        payload = await parse_body(request)
        data = validate(payload, schemas.CATEGORY_FIELDS, partial=partial)
        for key, value in data.items():
            setattr(category, key, value)
        category.save(session)
        return schemas.serialize_category(category), 200, {}


# --- articles ---------------------------------------------------------------------

class ArticleCollection(View):
    allow = COLLECTION_ALLOW
    authenticators = views.TOKEN_FIRST_AUTHENTICATORS
    permissions = {'GET': IS_AUTHENTICATED_OR_READ_ONLY,
                   'HEAD': IS_AUTHENTICATED_OR_READ_ONLY, 'POST': IS_AUTHENTICATED}
    title = 'Article List'

    async def get(self, request, session, user):
        search = request.query_params.get('search')
        categories = request.query_params.getlist('category')
        is_active = request.query_params.get('is_active')
        me = request.query_params.get('me')

        search_kwargs = {'title__icontains': search}
        if categories:
            search_kwargs['categories__id__in'] = categories

        me_kwargs = {'user': user}
        if is_active is not None and is_active in ['true', 'false']:
            me_kwargs['is_active'] = is_active.lower() == 'true'

        rules = [Search(search, **search_kwargs),
                 CategoryRule(categories, **search_kwargs),
                 Me(me, **me_kwargs)]

        kwargs = {}
        if not me:
            kwargs['is_active'] = True
        for rule in RulesFilter(rules).get_res():
            if rule.is_check():
                kwargs.update(rule.get_param())

        statement = select(Article)
        if 'title__icontains' in kwargs:
            statement = statement.where(
                func.lower(Article.title).contains(
                    str(kwargs['title__icontains']).lower()))
        if 'categories__id__in' in kwargs:
            statement = statement.where(Article.id.in_(
                select(article_categories.c.article_id).where(
                    article_categories.c.category_id.in_(
                        [int(value) for value in kwargs['categories__id__in']]))))
        if 'user' in kwargs:
            statement = statement.where(Article.user_id == _owner_pk(kwargs['user']))
        if 'is_active' in kwargs:
            statement = statement.where(Article.is_active.is_(kwargs['is_active']))
        rows = session.scalars(statement.order_by(Article.id.desc())).unique().all()
        if not rows:
            # An empty result is reported as a not-found, not as an empty page.
            raise NotFound('not_found')
        return paginate(request, rows, schemas.serialize_article_list), 200, {}

    async def post(self, request, session, user):
        payload = await parse_body(request)
        data = validate(payload, schemas.ARTICLE_FIELDS)
        category_ids = data.pop('categories', [])
        data.pop('user', None)
        article = Article(**data)
        article.user_id = user.id
        article.categories = _categories(session, category_ids)
        article.save(session)
        return schemas.serialize_article(article, session), 201, {}


class ArticleDetail(View):
    allow = ARTICLE_DETAIL_ALLOW
    authenticators = views.TOKEN_FIRST_AUTHENTICATORS
    permissions = {'GET': IS_AUTHENTICATED_OR_READ_ONLY,
                   'HEAD': IS_AUTHENTICATED_OR_READ_ONLY}
    default_permission = IS_AUTHENTICATED
    title = 'Article Instance'

    def get_object(self, request, session):
        id_or_slug = request.path_params['pk']
        if id_or_slug.isdigit():
            return _one(session, Article, Article.id == int(id_or_slug))
        return _one(session, Article, Article.slug == id_or_slug)

    async def get(self, request, session, user):
        return schemas.serialize_article(self.get_object(request, session), session), 200, {}

    async def put(self, request, session, user):
        return await self._write(request, session, user, partial=False)

    async def patch(self, request, session, user):
        return await self._write(request, session, user, partial=True)

    async def _write(self, request, session, user, partial):
        article = self.get_object(request, session)
        payload = await parse_body(request)
        data = validate(payload, schemas.ARTICLE_FIELDS, partial=partial)
        if 'is_approval' in data:
            if not user.is_staff and data['is_approval'] is True:
                raise ValidationFailed({'is_approval': [
                    'Onay durumunu sadece yöneticiler değiştirebilir.']})
            if data['is_approval'] is True:
                data['approval_user'] = user.id
            elif data['is_approval'] is False:
                data['approval_user'] = None
        if 'categories' in data:
            article.categories = _categories(session, data.pop('categories'))
        for key, value in data.items():
            if key in ('user', 'approval_user'):
                setattr(article, key + '_id', value)
            else:
                setattr(article, key, value)
        article.save(session)
        return schemas.serialize_article(article, session), 200, {}

    async def delete(self, request, session, user):
        article = self.get_object(request, session)
        # Soft delete. The collection filters only on is_active, so the row stays listed.
        article.is_delete = True
        session.add(article)
        session.flush()
        return None, 204, {}


# --- sliders ----------------------------------------------------------------------

class SliderCollection(View):
    allow = COLLECTION_ALLOW
    authenticators = views.TOKEN_FIRST_AUTHENTICATORS
    permissions = {'GET': IS_AUTHENTICATED_OR_READ_ONLY,
                   'HEAD': IS_AUTHENTICATED_OR_READ_ONLY, 'POST': IS_AUTHENTICATED}
    title = 'Slider List'

    async def get(self, request, session, user):
        search = request.query_params.get('search')
        me = request.query_params.get('me')
        rules = [Search(search, **{'title__icontains': search}),
                 Me(me, **{'user': user})]
        kwargs = {'is_active': True, 'is_delete': False}
        for rule in RulesFilter(rules).get_res():
            if rule.is_check():
                kwargs.update(rule.get_param())
        statement = select(Slider)
        if 'title__icontains' in kwargs:
            statement = statement.where(
                func.lower(Slider.title).contains(
                    str(kwargs['title__icontains']).lower()))
        if 'user' in kwargs:
            statement = statement.where(Slider.user_id == _owner_pk(kwargs['user']))
        statement = statement.where(Slider.is_active.is_(kwargs['is_active']),
                                    Slider.is_delete.is_(kwargs['is_delete']))
        rows = session.scalars(statement.order_by(Slider.id.desc())).unique().all()
        if not rows:
            raise NotFound('not_found')
        return paginate(request, rows, schemas.serialize_slider), 200, {}

    async def post(self, request, session, user):
        payload = await parse_body(request)
        data = validate(payload, schemas.SLIDER_FIELDS)
        data.pop('user', None)
        slider = Slider(**data)
        slider.user_id = user.id
        session.add(slider)
        session.flush()
        return schemas.serialize_slider(slider), 201, {}


class SliderDetail(View):
    allow = DETAIL_ALLOW
    authenticators = views.TOKEN_FIRST_AUTHENTICATORS
    permissions = {'GET': IS_AUTHENTICATED_OR_READ_ONLY,
                   'HEAD': IS_AUTHENTICATED_OR_READ_ONLY}
    default_permission = IS_AUTHENTICATED
    title = 'Slider Instance'

    def get_object(self, request, session):
        return _one(session, Slider, Slider.id == int(request.path_params['pk']))

    async def get(self, request, session, user):
        return schemas.serialize_slider(self.get_object(request, session)), 200, {}

    async def put(self, request, session, user):
        return await self._write(request, session, partial=False)

    async def patch(self, request, session, user):
        return await self._write(request, session, partial=True)

    async def _write(self, request, session, partial):
        slider = self.get_object(request, session)
        payload = await parse_body(request)
        data = validate(payload, schemas.SLIDER_FIELDS, partial=partial)
        for key, value in data.items():
            if key in ('user', 'approval_user'):
                setattr(slider, key + '_id', value)
            else:
                setattr(slider, key, value)
        session.add(slider)
        session.flush()
        return schemas.serialize_slider(slider), 200, {}


# --- comments ---------------------------------------------------------------------

class CommentCollection(View):
    allow = COLLECTION_ALLOW
    authenticators = views.TOKEN_FIRST_AUTHENTICATORS
    permissions = {'GET': ALLOW_ANY, 'HEAD': ALLOW_ANY, 'POST': ALLOW_ANY}
    title = 'Comment List'

    async def get(self, request, session, user):
        from core.models import ARTICLE_CONTENT_TYPE_ID, COMMENT_CONTENT_TYPE_ID
        search = request.query_params.get('search')
        comment_type = request.query_params.get('comment_type', 'article')
        parent_id = request.query_params.get('parent_id')
        statement = select(Comment).where(Comment.is_active.is_(True),
                                          Comment.is_delete.is_(False))
        if comment_type == 'article':
            statement = statement.where(
                Comment.content_type_id == ARTICLE_CONTENT_TYPE_ID,
                Comment.object_id.in_(select(Article.id).where(
                    Article.is_active.is_(True), Article.is_delete.is_(False))))
        elif comment_type == 'comment':
            statement = statement.where(
                Comment.content_type_id == COMMENT_CONTENT_TYPE_ID)
            if parent_id:
                statement = statement.where(Comment.object_id == int(parent_id))
        for rule in RulesFilter([Search(search, **{'name__icontains': search})]).get_res():
            if rule.is_check():
                value = rule.get_param().get('name__icontains')
                if value is not None:
                    statement = statement.where(
                        func.lower(Comment.name).contains(str(value).lower()))
        rows = session.scalars(statement.order_by(Comment.id.desc())).unique().all()
        return paginate(request, rows,
                        lambda row: schemas.serialize_comment(row, session)), 200, {}

    async def post(self, request, session, user):
        payload = await parse_body(request)
        data = validate(payload, schemas.COMMENT_FIELDS)
        data['content_type_id'] = data.pop('content_type')
        data.pop('user', None)
        comment = Comment(**data)
        if not user.is_anonymous:
            comment.user_id = user.id
        session.add(comment)
        session.flush()
        return schemas.serialize_comment(comment, session), 201, {}


class CommentDetail(View):
    allow = DETAIL_ALLOW
    authenticators = views.TOKEN_FIRST_AUTHENTICATORS
    default_permission = IS_AUTHENTICATED
    title = 'Comment Instance'

    def get_object(self, request, session):
        from core.models import ARTICLE_CONTENT_TYPE_ID
        row = session.scalar(select(Comment).where(
            Comment.id == int(request.path_params['pk']),
            Comment.is_active.is_(True), Comment.is_delete.is_(False),
            Comment.content_type_id == ARTICLE_CONTENT_TYPE_ID))
        if row is None:
            raise NotFound('No Comment matches the given query.')
        return row

    async def get(self, request, session, user):
        return schemas.serialize_comment(self.get_object(request, session),
                                         session), 200, {}

    async def put(self, request, session, user):
        return await self._write(request, session, user, partial=False)

    async def patch(self, request, session, user):
        return await self._write(request, session, user, partial=True)

    async def _write(self, request, session, user, partial):
        comment = self.get_object(request, session)
        if comment.user_id is None or comment.user_id != user.id:
            raise PermissionDenied('You must be the owner of this object.')
        payload = await parse_body(request)
        data = validate(payload, schemas.COMMENT_FIELDS, partial=partial)
        if 'content_type' in data:
            data['content_type_id'] = data.pop('content_type')
        data.pop('user', None)
        for key, value in data.items():
            setattr(comment, key, value)
        session.add(comment)
        session.flush()
        return schemas.serialize_comment(comment, session), 200, {}


# --- messages ---------------------------------------------------------------------

class MessageCollection(View):
    allow = COLLECTION_ALLOW
    authenticators = views.TOKEN_FIRST_AUTHENTICATORS
    default_permission = IS_AUTHENTICATED
    title = 'Message List'

    async def get(self, request, session, user):
        search = request.query_params.get('search')
        inbox = request.query_params.get('inbox')
        outbox = request.query_params.get('outbox')
        rules = [Search(search, **{'subject__icontains': search}),
                 Inbox(inbox, **{'user': user}),
                 Outbox(outbox, **{'sender': user})]
        kwargs = {}
        for rule in RulesFilter(rules).get_res():
            if rule.is_check():
                kwargs.update(rule.get_param())
        statement = visible_messages()
        if 'subject__icontains' in kwargs:
            statement = statement.where(func.lower(Message.subject).contains(
                str(kwargs['subject__icontains']).lower()))
        if 'user' in kwargs:
            statement = statement.where(Message.user_id == kwargs['user'].id)
        if 'sender' in kwargs:
            statement = statement.where(Message.sender_id == kwargs['sender'].id)
        statement = statement.where(or_(Message.user_id == user.id,
                                        Message.sender_id == user.id))
        rows = session.scalars(statement.order_by(Message.id.desc())).unique().all()
        return paginate(request, rows, schemas.serialize_message), 200, {}

    async def post(self, request, session, user):
        payload = await parse_body(request)
        data = validate(payload, schemas.MESSAGE_FIELDS)
        data.pop('created_at', None)
        sender = data.pop('sender', None)
        recipient = data.pop('user', None)
        message = Message(**data)
        message.sender_id = sender if sender is not None else user.id
        message.user_id = recipient
        session.add(message)
        session.flush()
        return schemas.serialize_message(message), 201, {}


class MessageDetail(View):
    allow = DETAIL_ALLOW
    authenticators = views.TOKEN_FIRST_AUTHENTICATORS
    default_permission = IS_AUTHENTICATED
    title = 'Message Instance'

    def get_object(self, request, session, user):
        row = session.scalar(visible_messages().where(
            Message.id == int(request.path_params['pk']),
            or_(Message.user_id == user.id, Message.sender_id == user.id)))
        if row is None:
            raise NotFound('No Message matches the given query.')
        return row

    async def get(self, request, session, user):
        return schemas.serialize_message(self.get_object(request, session, user)), 200, {}

    async def put(self, request, session, user):
        return await self._write(request, session, user, partial=False)

    async def patch(self, request, session, user):
        return await self._write(request, session, user, partial=True)

    async def _write(self, request, session, user, partial):
        message = self.get_object(request, session, user)
        payload = await parse_body(request)
        data = validate(payload, schemas.MESSAGE_FIELDS, partial=partial)
        data.pop('created_at', None)
        for key, value in data.items():
            if key in ('sender', 'user'):
                setattr(message, key + '_id', value)
            else:
                setattr(message, key, value)
        session.add(message)
        session.flush()
        return schemas.serialize_message(message), 200, {}


# --- helpers ----------------------------------------------------------------------

class DoesNotExist(Exception):
    """Raised by a detail route when its row is not there, as the old manager did."""


def _owner_pk(owner):
    """The owner filter binds the user OBJECT, not its key.

    A caller with no row behind it therefore cannot be bound at all, so an owner filter
    from an anonymous caller fails rather than quietly matching rows with no owner.
    """
    if getattr(owner, 'pk', None) is None:
        raise TypeError('Field "user" expected a number but got %s.' % owner)
    return owner.pk


def _one(session, model, condition):
    row = session.scalar(select(model).where(condition))
    if row is None:
        raise DoesNotExist('%s matching query does not exist.' % model.__name__)
    return row


def _categories(session, ids):
    rows = session.scalars(select(Category).where(Category.id.in_(list(ids)))).all()
    by_id = {row.id: row for row in rows}
    return [by_id[value] for value in ids if value in by_id]
