"""The generic view mixins, kept in their own module like the framework had."""
from app.api.views import (  # noqa: F401
    CreateModelMixin,
    DestroyModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
)
