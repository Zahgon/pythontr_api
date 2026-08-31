"""A small, Flask-native REST toolkit used across the project.

The original project leaned on Django REST Framework for routing, request
authentication, permission checks, pagination and error rendering.  Flask has
no equivalent batteries, so the pieces this project actually used live here:
``MethodView`` based views with the same action vocabulary, a router that
produces the same URL shapes, permission callables, and an exception hierarchy
that renders the same JSON error bodies.
"""
