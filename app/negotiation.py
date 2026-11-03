"""Renderer selection.

Two renderers are offered, JSON first and the browsable HTML page second. A format suffix
on the path outranks ``?format=``, which outranks ``Accept``.
"""

from app.wire import NotAcceptable

JSON = 'json'
API = 'api'
RENDERERS = (JSON, API)
MEDIA_TYPES = {JSON: 'application/json', API: 'text/html'}

FORMAT_QUERY_PARAM = 'format'


def selected(request):
    """Return ``'json'`` or ``'api'``, or raise.

    A suffix already removed from the path by :class:`app.middleware.FormatSuffixMiddleware`
    is read back off the scope. An unknown format is a 404 -- raised before ``Accept`` is
    looked at and before the caller is identified. The match is case sensitive, an empty
    ``?format=`` is ignored, and the last repeat wins.
    """
    from app.wire import NotFound

    suffix = request.scope.get('format_suffix')
    if suffix:
        if suffix not in RENDERERS:
            raise NotFound()
        return suffix

    values = [value for value in request.query_params.getlist(FORMAT_QUERY_PARAM) if value]
    if values:
        wanted = values[-1]
        if wanted not in RENDERERS:
            raise NotFound()
        return wanted

    accept = request.headers.get('accept', '')
    if not accept.strip():
        return JSON
    offered = []
    for part in accept.split(','):
        token = part.split(';', 1)[0].strip().lower()
        if token in ('*/*', 'application/*', 'application/json'):
            offered.append(JSON)
        elif token in ('text/*', 'text/html'):
            offered.append(API)
    if not offered:
        raise NotAcceptable()
    return offered[0]
