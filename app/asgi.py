"""
ASGI config for app project.

It exposes the ASGI callable as a module-level variable named ``application``.
"""

from asgiref.wsgi import WsgiToAsgi

from app import create_app

application = WsgiToAsgi(create_app())
