"""The browsable HTML page that ``?format=api`` serves.

It is a developer convenience, not a client contract: what is contractual is that the page
is ``text/html; charset=utf-8``, that it sets a ``csrftoken`` cookie, and that the
response varies on ``Accept`` and ``Cookie``.
"""

import html

from app.security import get_random_string
from app.wire import dumps

MEDIA_TYPE = 'text/html; charset=utf-8'
CSRF_COOKIE = 'csrftoken'
CSRF_TOKEN_LENGTH = 32
CSRF_ALLOWED_CHARS = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'

_PAGE = """<!DOCTYPE html>
<html lang="tr">
  <head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>
    <meta name="robots" content="NONE,NOARCHIVE" />
    <title>{title}</title>
  </head>
  <body>
    <div class="wrapper">
      <h1>{title}</h1>
      <div class="request-info"><pre>{method} {path}</pre></div>
      <div class="response-info"><pre>HTTP {status}
Content-Type: application/json

{payload}</pre></div>
    </div>
  </body>
</html>
"""


def new_csrf_token():
    return get_random_string(CSRF_TOKEN_LENGTH, CSRF_ALLOWED_CHARS)


def wants_html(renderer):
    return renderer == 'api'


def render(request, payload, status_code, title):
    body = html.escape(dumps(payload).decode('utf-8')) if payload is not None else ''
    return _PAGE.format(title=html.escape(title), method=request.method,
                        path=html.escape(request.url.path), status=status_code,
                        payload=body)
