from .model_content_type import * # noqa
from .model_token import * # noqa
from .model_user import * # noqa
from .model_category import * # noqa
from .model_comment import * # noqa
from .model_article import * # noqa
from .model_message import * # noqa
from .model_slider import * # noqa
from .model_page_visit import * # noqa
from .model_activation import * # noqa

from .model_article import Article
from .model_category import Category
from .model_comment import Comment
from .model_content_type import ContentType  # noqa: F401
from .model_message import Message
from .model_page_visit import PageVisit
from .model_slider import Slider
from .model_token import Token  # noqa: F401
from .model_user import User

#: Rows that ``django_content_type`` is populated with, in the order Django's
#: ``migrate`` created them.  ``Comment.content_object`` resolves through this.
CONTENT_TYPE_MODELS = (
    User,
    Category,
    Comment,
    Article,
    Message,
    Slider,
    PageVisit,
)


def get_user_model():
    """``get_user_model`` — ``AUTH_USER_MODEL`` is fixed to this one."""
    return User
