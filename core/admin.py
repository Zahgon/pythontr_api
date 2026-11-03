"""The model registry.

The old stack rendered a server-side administration site from these registrations. Bare
Starlette has no administration framework and none is reimplemented, so this module is now
a registry with no HTTP surface: nothing is served under ``/admin``. The staff JSON API
under ``/api/user/admin/`` is unaffected and is where staff work happens.
"""

from core import models


class ModelAdmin:
    list_display = ()
    list_filter = ()
    search_fields = ()
    readonly_fields = ()
    can_add = True


class UserAdmin(ModelAdmin):
    ordering = ['id']
    readonly_fields = ('created_at', 'slug')
    list_display = ('email', 'username', 'name', 'surname',
                    'created_at', 'updated_at', 'last_login')
    list_filter = ('email',)


class ArticleAdmin(ModelAdmin):
    list_display = ('id', 'created_at', 'title', 'title_h1', 'is_active', 'is_delete')
    list_filter = ('id', 'title', 'title_h1')
    search_fields = ('id', 'title', 'title_h1')


class CommentAdmin(ModelAdmin):
    list_display = ('id', 'created_at', 'content', 'content_object',
                    'is_active', 'is_delete')
    list_filter = ('id', 'content')
    search_fields = ('id', 'content')


class PageVisitAdmin(ModelAdmin):
    list_display = ('id', 'user', 'path', 'timestamp', 'ip_address', 'user_agent',
                    'referrer', 'method', 'device_type', 'language', 'ga_client_id',
                    'ga_session_id', 'gads_id', 'gpi_uid')
    list_filter = ('id', 'user', 'path', 'device_type', 'method', 'timestamp')
    search_fields = ('id', 'user', 'path')
    readonly_fields = ['timestamp']
    can_add = False


REGISTRY = {}


def register(model, admin_class=ModelAdmin):
    REGISTRY[model.__name__.lower()] = admin_class()


def registered_models():
    return sorted(REGISTRY)


def find(name):
    return REGISTRY.get(name)


register(models.User, UserAdmin)
register(models.Category)
register(models.Article, ArticleAdmin)
register(models.Comment, CommentAdmin)
register(models.Message)
register(models.PageVisit, PageVisitAdmin)
