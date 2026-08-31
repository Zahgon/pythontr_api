from flask import Blueprint

from app.api.routers import DefaultRouter

from recipe import views

# /api/recipe/categories/1/
router = DefaultRouter()
router.register('categories', views.CategoryViewSet)
router.register('articles', views.ArticleViewSet)
router.register('sliders', views.SliderViewSet)
router.register('comments', views.CommentViewSet)
router.register('messages', views.MessageViewSet)
app_name = 'recipe'

blueprint = Blueprint(app_name, __name__)
router.register_urls(blueprint)
