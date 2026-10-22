"""Content negotiation, the way the previous framework did it.

Every API view picked its renderer before it authenticated anybody: from the
``format`` URL suffix or ``?format=`` query parameter when one was given,
otherwise from the ``Accept`` header.  A format nobody renders answered 404
and an ``Accept`` header nobody satisfies answered 406, both ahead of any
authentication, permission or method check.  The JSON renderer honoured an
``indent`` media-type parameter.  This module reproduces that selection; the
dispatcher in ``app.api.views`` applies it.
"""
from app.api.exceptions import NotAcceptable, NotFound


class Renderer:

    def __init__(self, media_type, format):
        self.media_type = media_type
        self.format = format


JSON = Renderer('application/json', 'json')
#: The browsable API.  It is negotiated like before, but rendered as JSON:
#: the HTML pages were a development aid, not part of the service.
BROWSABLE = Renderer('text/html', 'api')
RENDERERS = (JSON, BROWSABLE)

#: The indent the JSON renderer accepted, clamped the same way.
MAX_INDENT = 8


class MediaType:

    def __init__(self, text):
        self.orig = (text or '').strip()
        base, _, params = self.orig.partition(';')
        self.full_type = base.strip().lower()
        self.main_type, _, self.sub_type = self.full_type.partition('/')
        self.params = {}
        for param in params.split(';'):
            key, sep, value = param.partition('=')
            if sep:
                self.params[key.strip()] = value.strip()

    def match(self, other):
        """Whether this (renderer) media type satisfies the client's ``other``.

        Only the renderer's own parameters have to agree, so a client
        parameter such as ``indent`` never stops a match.
        """
        for key in self.params:
            if key != 'q' and other.params.get(key) != self.params[key]:
                return False
        if self.sub_type != '*' and other.sub_type != '*' \
                and other.sub_type != self.sub_type:
            return False
        if self.main_type != '*' and other.main_type != '*' \
                and other.main_type != self.main_type:
            return False
        return True

    @property
    def precedence(self):
        if self.main_type == '*':
            return 0
        if self.sub_type == '*':
            return 1
        if not self.params or list(self.params) == ['q']:
            return 2
        return 3


def _accept_list(request):
    header = request.headers.get('Accept')
    if header is None:
        header = '*/*'
    return [token.strip() for token in header.split(',')]


def select_renderer(request, format_suffix=None):
    """Return ``(renderer, accepted media type)`` or raise 404 / 406."""
    renderers = RENDERERS
    format_query = format_suffix or request.args.get('format')
    if format_query:
        renderers = [r for r in RENDERERS if r.format == format_query]
        if not renderers:
            raise NotFound()

    accepts = [MediaType(token) for token in _accept_list(request)]
    for precedence in (3, 2, 1, 0):
        group = [media for media in accepts if media.precedence == precedence]
        for renderer in renderers:
            renderer_type = MediaType(renderer.media_type)
            for media in group:
                if renderer_type.match(media):
                    if '*' in media.full_type:
                        return renderer, renderer_type
                    return renderer, media
    raise NotAcceptable()


def indent_for(accepted):
    """The JSON indent an accepted ``...; indent=N`` asked for, else None."""
    try:
        indent = int(accepted.params['indent'])
    except (KeyError, TypeError, ValueError):
        return None
    indent = max(min(indent, MAX_INDENT), 0)
    return indent or None
