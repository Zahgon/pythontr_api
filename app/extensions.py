"""Flask extension singletons.

They live in their own module so that models, views and the application
factory can import them without creating a circular import.
"""

from flask_admin import Admin
from flask_babel import Babel
from flask_cors import CORS
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for every model in the project."""


db = SQLAlchemy(model_class=Base)
migrate = Migrate()
babel = Babel()
cors = CORS()
login_manager = LoginManager()
admin_site = Admin(name='pythontr_api', template_mode='bootstrap4')
