"""Named routes and reverse resolution.

``reverse`` answers the names the project used. ``user:reset-password-confirm`` is
registered twice -- once with no arguments and once with ``uidb64`` and ``token`` -- and is
disambiguated by how many arguments the caller supplies, exactly as before.
"""

FORMAT_SUFFIX_PREFIXES = ('/api/recipe', '/api/user/admin')
FORMAT_SUFFIXES = ('json', 'api')


class NoReverseMatch(Exception):
    pass


_ROUTES = {
    'recipe:api-root': '/api/recipe/',
    'recipe:category-list': '/api/recipe/categories/',
    'recipe:category-detail': '/api/recipe/categories/{pk}/',
    'recipe:article-list': '/api/recipe/articles/',
    'recipe:article-detail': '/api/recipe/articles/{pk}/',
    'recipe:slider-list': '/api/recipe/sliders/',
    'recipe:slider-detail': '/api/recipe/sliders/{pk}/',
    'recipe:comment-list': '/api/recipe/comments/',
    'recipe:comment-detail': '/api/recipe/comments/{pk}/',
    'recipe:message-list': '/api/recipe/messages/',
    'recipe:message-detail': '/api/recipe/messages/{pk}/',
    'user:create': '/api/user/create/',
    'user:token': '/api/user/token/',
    'user:me': '/api/user/me/',
    'user:activate': '/api/user/activate/{code}/',
    'user:resend-activation': '/api/user/resend-activation/',
    'user:reset-password': '/api/user/reset-password/',
    'user:admin:api-root': '/api/user/admin/',
    'user:admin:users-list': '/api/user/admin/users/',
    'user:admin:users-detail': '/api/user/admin/users/{pk}/',
    'user:admin:page-visits-list': '/api/user/admin/page-visits/',
    'user:admin:page-visits-detail': '/api/user/admin/page-visits/{pk}/',
}

# The duplicate registration, keyed by argument count.
_RESET_CONFIRM = {
    0: '/api/user/reset-password/confirm/',
    2: '/api/user/reset-password/confirm/{uidb64}/{token}/',
}


def reverse(name, args=None, kwargs=None):
    args = list(args or [])
    kwargs = dict(kwargs or {})
    if name == 'user:reset-password-confirm':
        count = len(args) + len(kwargs)
        if count not in _RESET_CONFIRM:
            raise NoReverseMatch(name)
        template = _RESET_CONFIRM[count]
    else:
        if name not in _ROUTES:
            raise NoReverseMatch(name)
        template = _ROUTES[name]
    names = [part.split('}')[0] for part in template.split('{')[1:]]
    if args:
        if len(args) != len(names):
            raise NoReverseMatch(name)
        kwargs = dict(zip(names, args))
    if sorted(kwargs) != sorted(names):
        raise NoReverseMatch(name)
    return template.format(**{key: str(value) for key, value in kwargs.items()})


def nodot(segment):
    """The path convertor the detail routes use: one segment with no dot in it."""
    return '.' not in segment and segment != ''


def split_format_suffix(path):
    """Split ``('/api/recipe/categories/1/', 'json')`` off ``/api/recipe/categories/1.json``.

    Only the two prefixes above carry suffixes. The last segment must be a bare name with
    exactly ONE dot in it and a lower-case known suffix, so an upper-case suffix, a bare
    dot, an empty name or two suffixes do not split and therefore miss the route. The
    remaining path always ends in a slash, so both ``…/1.json`` and ``…/1.json/`` resolve.
    """
    if not path.startswith(FORMAT_SUFFIX_PREFIXES):
        return path, None
    stem = path[:-1] if path.endswith('/') else path
    head, _, last = stem.rpartition('/')
    if last.count('.') != 1:
        return path, None
    name, _, suffix = last.partition('.')
    if not name or suffix not in FORMAT_SUFFIXES:
        return path, None
    return '%s/%s/' % (head, name), suffix


def suffixed(path, suffix):
    if not suffix:
        return path
    trailing = path.endswith('/')
    stem = path[:-1] if trailing else path
    return '%s.%s%s' % (stem, suffix, '/' if trailing else '')
