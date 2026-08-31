from recipe.urls import blueprint as recipe_urls
from user.urls import blueprint as user_urls

# admin/ is mounted by core.admin, static files by the application factory.
urlpatterns = [
    ('/api/user', user_urls),
    ('/api/recipe', recipe_urls),
]


def register_blueprints(app):
    for url_prefix, blueprint in urlpatterns:
        app.register_blueprint(blueprint, url_prefix=url_prefix)
