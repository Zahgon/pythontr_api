"""Status codes, JSON byte layout, error envelopes and the page envelope.

Every route answers through here rather than building a response of its own, so the byte
layout and the envelope shapes are decided in one place.

The Turkish strings below were produced by a compiled catalogue that the old framework
shipped inside its own package. That package is gone, so they are written out literally.
Project message keys are the other half of the vocabulary and are NOT written out: they
travel as keys, which is what :mod:`app.i18n` reproduces.
"""

import json
import re
from urllib.parse import urlencode, urlparse

from starlette.responses import Response

JSON_MEDIA_TYPE = 'application/json'
HTML_MEDIA_TYPE = 'text/html; charset=utf-8'


def stamp(value):
    """A timestamp as the API published it: ISO 8601, microseconds, trailing ``Z``."""
    if value is None:
        return None
    return value.replace(tzinfo=None).isoformat() + 'Z'


def dumps(payload):
    """Compact JSON: no spaces, no escaping of non-ASCII, no trailing newline."""
    return json.dumps(payload, separators=(',', ':'), ensure_ascii=False).encode('utf-8')


class JSONResponse(Response):
    media_type = JSON_MEDIA_TYPE

    def render(self, content):
        if content is None:
            return b''
        return dumps(content)


def json_response(payload, status_code=200, headers=None):
    if status_code == 204:
        # No body and no content type, which is what a 204 carried before.
        return Response(status_code=204, headers=headers)
    return JSONResponse(payload, status_code=status_code, headers=headers)


class ApiError(Exception):
    status_code = 500
    default_detail = 'Bir hata oluştu.'

    def __init__(self, detail=None, status_code=None):
        self.detail = self.default_detail if detail is None else detail
        if status_code is not None:
            self.status_code = status_code
        super().__init__(str(self.detail))

    def body(self):
        """A scalar detail renders as ``{"detail": ...}``; a dict or list stands alone."""
        if isinstance(self.detail, (dict, list)):
            return self.detail
        return {'detail': str(self.detail)}


class NotAuthenticated(ApiError):
    status_code = 401
    default_detail = 'Giriş bilgileri verilmedi.'


class AuthenticationFailed(ApiError):
    status_code = 401
    default_detail = 'Geçersiz token.'


class PermissionDenied(ApiError):
    status_code = 403
    default_detail = 'Bu işlemi yapmak için izniniz bulunmuyor.'


class NotFound(ApiError):
    status_code = 404
    default_detail = 'Bulunamadı.'


class MethodNotAllowed(ApiError):
    status_code = 405

    def __init__(self, method):
        super().__init__('"%s" metoduna izin verilmiyor.' % method)


class UnsupportedMediaType(ApiError):
    status_code = 415

    def __init__(self, media_type):
        super().__init__('İstekte desteklenmeyen medya tipi: "%s".' % media_type)


class NotAcceptable(ApiError):
    status_code = 406
    default_detail = ('İsteğe ait Accept başlık bilgisi yanıt verilecek '
                      'başlık bilgileri arasında değil.')


class ParseError(ApiError):
    status_code = 400
    default_detail = 'Hatalı istek.'


class ValidationFailed(ApiError):
    """A 400 whose body is the field-error mapping exactly as it was built."""

    status_code = 400

    def __init__(self, errors):
        super().__init__(errors)


def error_response(error):
    return json_response(error.body(), status_code=error.status_code)


# --- Allow bookkeeping ------------------------------------------------------------
# The verb set a route advertises is recorded on the request while it is being handled,
# so the middleware that writes the header does not need to know the routing table.

def set_allow(request, allow):
    request.scope['allow'] = allow


def get_allow(request):
    return request.scope.get('allow')


# --- page envelope ----------------------------------------------------------------

PAGE_QUERY_PARAM = 'page'


def page_size():
    from app import settings
    return settings.API.get('PAGE_SIZE')


def _link(request, page_number):
    if page_number is None:
        return None
    params = dict(request.query_params)
    if page_number == 1:
        params.pop(PAGE_QUERY_PARAM, None)
    else:
        params[PAGE_QUERY_PARAM] = str(page_number)
    query = urlencode(params)
    path = urlparse(str(request.url)).path
    return '%s?%s' % (path, query) if query else path


def paginate(request, rows, serialize):
    """Slice ``rows`` into the page envelope, or pass them through unpaginated.

    Key order is ``count``, ``first_page``, ``last_page``, ``next``, ``previous``,
    ``last_page_number``, ``current_page``, ``results``. ``first_page`` is the previous
    link with ``?page=<n>`` deleted by a regular expression -- which removes the question
    mark with it, so any other parameter that survives is joined on with a bare ``&``.
    ``last_page`` is the next link renumbered to the final page.
    """
    size = page_size()
    rows = list(rows)
    if not size:
        return {'results': [serialize(row) for row in rows], 'unpaginated': True}

    count = len(rows)
    num_pages = max(1, (count + size - 1) // size)
    raw = request.query_params.get(PAGE_QUERY_PARAM)
    if raw in (None, ''):
        number = 1
    elif raw == 'last':
        number = num_pages
    else:
        try:
            number = int(raw)
        except ValueError:
            raise NotFound('Geçersiz sayfa.')
        if number < 1 or number > num_pages:
            raise NotFound('Geçersiz sayfa.')

    start = (number - 1) * size
    page_rows = rows[start:start + size]
    next_link = _link(request, number + 1) if number < num_pages else None
    previous_link = _link(request, number - 1) if number > 1 else None
    first_page = re.sub(r'\?page=\d+', '', previous_link) if previous_link else None
    last_page = re.sub(r'\?page=\d+', '?page={}'.format(num_pages),
                       next_link) if next_link else None
    return {
        'count': count,
        'first_page': first_page,
        'last_page': last_page,
        'next': next_link,
        'previous': previous_link,
        'last_page_number': num_pages,
        'current_page': number,
        'results': [serialize(row) for row in page_rows],
    }
