"""View decorators, re-exported so views can spell ``import action``."""
from app.api.views import action  # noqa: F401

__all__ = ['action']
