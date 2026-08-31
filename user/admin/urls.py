from flask import Blueprint

from app.api.routers import DefaultRouter
from user.admin.views.view_user_admin import AdminUserViewSet
from user.admin.views.view_page_visit import PageVisitViewSet

app_name = 'admin'  # admin namespace için gerekli

router = DefaultRouter()
router.register('users', AdminUserViewSet, basename='users')
router.register('page-visits', PageVisitViewSet, basename='page-visits')

blueprint = Blueprint(app_name, __name__)
router.register_urls(blueprint)
