"""The staff JSON API.

Preserved rather than repaired:

* the page-visit document names ``session_id`` and ``extra_data``, two columns the table
  does not have, so any read of a populated list or row raises -- and so does the
  ``OPTIONS`` metadata that describes the same document;
* content performance averages ``time_spent``, also absent, so it raises;
* the three analytics actions are allow-any and narrow on the CALLER's id, which is
  ``None`` for an anonymous caller, so anonymous sees every row and an identified caller
  sees only rows whose ``user`` is themselves -- and ``user`` holds the ARTICLE OWNER, not
  the visitor;
* a page visit recorded from a loopback address raises, because the extractor returns
  nothing and the caller reads a key off it straight away.
"""

import re
from datetime import timedelta

from sqlalchemy import func, select, update
from user_agents import parse

from app.parsing import Field, parse_body, validate
from app.views import ALLOW_ANY, IS_ADMIN, View
from app.wire import NotFound, paginate
from app.wire import stamp as _stamp
from core.models import Article, PageVisit, User, utcnow

LIST_ALLOW = 'GET'
DETAIL_ALLOW = 'GET, PATCH, DELETE'
VISIT_LIST_ALLOW = 'GET, POST, HEAD, OPTIONS'
VISIT_DETAIL_ALLOW = 'GET, PUT, PATCH, DELETE, HEAD, OPTIONS'
ACTION_GET_ALLOW = 'GET, HEAD, OPTIONS'
ACTION_POST_ALLOW = 'POST, OPTIONS'

#: The page-visit document. `session_id` and `extra_data` are not columns.
PAGE_VISIT_KEYS = ('id', 'user', 'path', 'timestamp', 'ip_address', 'user_agent',
                   'referrer', 'method', 'device_type', 'language', 'session_id',
                   'extra_data')


class ApiRoot(View):
    allow = 'GET, HEAD, OPTIONS'
    permissions = {'GET': ALLOW_ANY, 'HEAD': ALLOW_ANY, 'OPTIONS': ALLOW_ANY}
    title = 'Api Root'

    async def get(self, request, session, user):
        from app.urls import suffixed
        base = str(request.base_url).rstrip('/')
        suffix = request.scope.get('format_suffix')
        return ({'users': base + suffixed('/api/user/admin/users/', suffix),
                 'page-visits': base + suffixed('/api/user/admin/page-visits/', suffix)},
                200, {})


LIST_KEYS = ('id', 'username', 'email', 'name', 'surname', 'image', 'is_active',
             'is_staff', 'is_ban', 'is_delete', 'created_at', 'updated_at')


def serialize_user_list(account):
    return {
        'id': account.id, 'username': account.username, 'email': account.email,
        'name': account.name, 'surname': account.surname, 'image': account.image,
        'is_active': account.is_active, 'is_staff': account.is_staff,
        'is_ban': account.is_ban, 'is_delete': account.is_delete,
        'created_at': _stamp(account.created_at),
        'updated_at': _stamp(account.updated_at),
    }


def serialize_user_detail(account):
    payload = serialize_user_list(account)
    ordered = {}
    for key in ('id', 'username', 'email', 'name', 'surname', 'image'):
        ordered[key] = payload[key]
    ordered['about_me'] = account.about_me
    for key in ('is_active', 'is_staff', 'is_ban', 'is_delete', 'created_at',
                'updated_at'):
        ordered[key] = payload[key]
    return ordered


def serialize_user_action(account):
    return {'is_active': account.is_active, 'is_staff': account.is_staff,
            'is_ban': account.is_ban, 'is_delete': account.is_delete}


ACTION_FIELDS = (Field('is_active', required=False, kind='boolean'),
                 Field('is_staff', required=False, kind='boolean'),
                 Field('is_ban', required=False, kind='boolean'),
                 Field('is_delete', required=False, kind='boolean'))

FLAGS = {'is_active': User.is_active, 'is_staff': User.is_staff, 'is_ban': User.is_ban}


def _flag(value):
    """``true``/``false`` and ``1``/``0`` are read; anything else is ignored."""
    text = (value or '').strip().lower()
    if text in ('true', '1'):
        return True
    if text in ('false', '0'):
        return False
    return None


class UserCollection(View):
    allow = LIST_ALLOW
    default_permission = IS_ADMIN
    title = 'Admin User List'

    async def get(self, request, session, user):
        statement = select(User)
        search = request.query_params.get('search')
        if search:
            needle = search.lower()
            statement = statement.where(
                func.lower(User.email).contains(needle)
                | func.lower(User.name).contains(needle)
                | func.lower(User.surname).contains(needle))
        for name, column in FLAGS.items():
            raw = request.query_params.get(name)
            if raw is None:
                continue
            wanted = _flag(raw)
            if wanted is not None:
                statement = statement.where(column.is_(wanted))
        rows = session.scalars(
            statement.order_by(User.created_at.desc(), User.id.desc())).unique().all()
        return paginate(request, rows, serialize_user_list), 200, {}


class UserDetail(View):
    allow = DETAIL_ALLOW
    default_permission = IS_ADMIN
    title = 'Admin User Instance'

    def get_object(self, request, session):
        """Loads the row directly; a row that is not there raises."""
        from recipe.routes import DoesNotExist
        account = session.get(User, int(request.path_params['pk']))
        if account is None:
            raise DoesNotExist('User matching query does not exist.')
        return account

    async def get(self, request, session, user):
        return serialize_user_detail(self.get_object(request, session)), 200, {}

    async def patch(self, request, session, user):
        account = self.get_object(request, session)
        if account.id == user.id:
            return {'error': 'you_cannot_modify_your_own_account'}, 400, {}
        payload = await parse_body(request)
        data = validate(payload, ACTION_FIELDS, partial=True)
        for key, value in data.items():
            setattr(account, key, value)
        session.add(account)
        session.flush()
        return serialize_user_action(account), 200, {}

    async def delete(self, request, session, user):
        account = self.get_object(request, session)
        if account.id == user.id:
            return {'error': 'you_cannot_delete_your_own_account'}, 400, {}
        # Marks the account only; it stays in the directory.
        account.is_delete = True
        session.add(account)
        session.flush()
        return None, 204, {}


def serialize_page_visit(visit):
    """Reads every key the document names, including the two the table lacks."""
    return {
        'id': visit.id,
        'user': visit.user_id,
        'path': visit.path,
        'timestamp': _stamp(visit.timestamp),
        'ip_address': visit.ip_address,
        'user_agent': visit.user_agent,
        'referrer': visit.referrer,
        'method': visit.method,
        'device_type': visit.device_type,
        'language': visit.language,
        'session_id': visit.session_id,
        'extra_data': visit.extra_data,
    }


class PageVisitCollection(View):
    allow = VISIT_LIST_ALLOW
    default_permission = IS_ADMIN
    title = 'Page Visit List'

    async def get(self, request, session, user):
        rows = session.scalars(
            select(PageVisit).order_by(PageVisit.timestamp.desc(),
                                       PageVisit.id.desc())).unique().all()
        return paginate(request, rows, serialize_page_visit), 200, {}

    async def post(self, request, session, user):
        payload = await parse_body(request)
        data = validate(payload, VISIT_FIELDS, partial=True)
        visit = PageVisit(path=data.get('path', request.url.path),
                          method=data.get('method', request.method))
        for key, value in data.items():
            if key in ('path', 'method'):
                continue
            setattr(visit, key, value)
        session.add(visit)
        session.flush()
        return serialize_page_visit(visit), 201, {}

    def options_payload(self):
        # Describes the same document, so it reads the same absent columns.
        return {'name': self.title,
                'actions': {'POST': {key: {'type': 'field'}
                                     for key in PAGE_VISIT_KEYS}},
                'fields': [getattr(PageVisit, key).key for key in PAGE_VISIT_KEYS]}


VISIT_FIELDS = (Field('path', required=False), Field('content_id', required=False,
                                                     allow_null=True, kind='integer'),
                Field('ip_address', required=False, allow_null=True),
                Field('user_agent', required=False, allow_null=True),
                Field('referrer', required=False, allow_null=True),
                Field('method', required=False),
                Field('device_type', required=False),
                Field('language', required=False, allow_null=True))


class PageVisitDetail(View):
    allow = VISIT_DETAIL_ALLOW
    default_permission = IS_ADMIN
    title = 'Page Visit Instance'

    def get_object(self, request, session):
        visit = session.get(PageVisit, int(request.path_params['pk']))
        if visit is None:
            raise NotFound('No PageVisit matches the given query.')
        return visit

    async def get(self, request, session, user):
        return serialize_page_visit(self.get_object(request, session)), 200, {}

    async def put(self, request, session, user):
        return await self._write(request, session, partial=False)

    async def patch(self, request, session, user):
        return await self._write(request, session, partial=True)

    async def _write(self, request, session, partial):
        visit = self.get_object(request, session)
        payload = await parse_body(request)
        data = validate(payload, VISIT_FIELDS, partial=partial)
        for key, value in data.items():
            setattr(visit, key, value)
        session.add(visit)
        session.flush()
        return serialize_page_visit(visit), 200, {}

    async def delete(self, request, session, user):
        visit = self.get_object(request, session)
        session.delete(visit)
        session.flush()
        return None, 204, {}


BOT_STRINGS = [
    'bot', 'crawler', 'spider', 'ping', 'lighthouse',
    'slurp', 'search', 'surveillance', 'monitoring',
    'analyzer', 'index', 'archive', 'scrape',
    'http', 'python-requests', 'curl', 'wget',
    'phantom', 'headless', 'selenium',
    'mediapartners-google', 'adsbot-google',
]


def _is_bot(ua_string, user_agent):
    return any(bot in ua_string.lower() for bot in BOT_STRINGS) or user_agent.is_bot


async def _request_data(request, session):
    """Nothing is returned for a loopback address, and the caller reads a key anyway."""
    ip_address = (request.headers.get('x-forwarded-for', '')
                  or request.headers.get('x-real-ip', '')
                  or (request.client.host if request.client else '')
                  ).split(',')[0].strip()
    if ip_address in ('127.0.0.1', '::1', 'localhost'):
        return None
    body_data = await parse_body(request)
    path = body_data.get('path', request.url.path)
    content_id = None
    match = re.search(r'(.*?)-(\d+)$', path)
    if match:
        content_id = match.group(2)
        session.execute(update(Article).where(Article.id == int(content_id))
                        .values(read_count=Article.read_count + 1))
    return {
        'path': path,
        'content_id': content_id,
        'referrer': body_data.get('referrer', request.headers.get('referer')),
        'ip_address': ip_address,
        'language': (request.headers.get('accept-language') or 'en')[:10],
        'user_agent': request.headers.get('user-agent', ''),
        'ga_client_id': request.cookies.get('_ga'),
        'ga_session_id': request.cookies.get('_ga_369S5MD2X3'),
        'gads_id': request.cookies.get('__gads'),
        'gpi_uid': request.cookies.get('__gpi'),
    }


class TrackPageVisit(View):
    allow = ACTION_POST_ALLOW
    # The action is allow-any as a whole, so an unadvertised verb reaches the 405 rather
    # than being refused for want of a credential.
    default_permission = ALLOW_ANY
    title = 'Track Page Visit'

    async def post(self, request, session, user):
        data = await _request_data(request, session)
        user_agent = parse(data['user_agent'])
        if _is_bot(data['user_agent'], user_agent):
            return {'status': 'ignored', 'reason': 'bot_detected'}, 200, {}
        content_owner = None
        if data['content_id']:
            article = session.get(Article, int(data['content_id']))
            if article is not None:
                content_owner = article.user_id
        visit = PageVisit(
            user_id=content_owner,
            path=data['path'],
            content_id=int(data['content_id']) if data['content_id'] else None,
            ip_address=data['ip_address'],
            user_agent=data['user_agent'],
            referrer=data['referrer'],
            method=request.method,
            language=data['language'],
            device_type=('mobile' if user_agent.is_mobile else
                         'tablet' if user_agent.is_tablet else 'desktop'),
            browser=user_agent.browser.family,
            os=user_agent.os.family,
            device_brand=user_agent.device.brand,
            device_model=user_agent.device.model,
            ga_client_id=data['ga_client_id'],
            ga_session_id=data['ga_session_id'],
            gads_id=data['gads_id'],
            gpi_uid=data['gpi_uid'],
        )
        session.add(visit)
        session.flush()
        return {'status': 'success'}, 200, {}


def _date_range(period):
    now = utcnow()
    if period == 'day':
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == 'week':
        start = (now - timedelta(days=now.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0)
    elif period == 'month':
        start = (now - timedelta(days=30)).replace(hour=0, minute=0, second=0,
                                                   microsecond=0)
    elif period == 'year':
        start = (now - timedelta(days=365)).replace(hour=0, minute=0, second=0,
                                                    microsecond=0)
    else:
        return None, None
    return start, now


class _Analytics(View):
    allow = ACTION_GET_ALLOW
    default_permission = ALLOW_ANY

    def filtered(self, request, user, statement):
        period = request.query_params.get('period')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        if start_date and end_date:
            statement = statement.where(PageVisit.timestamp.between(start_date, end_date))
        elif period:
            start, end = _date_range(period)
            if start and end:
                statement = statement.where(PageVisit.timestamp.between(start, end))
        # `None` for an anonymous caller, so no narrowing happens at all.
        if user.id:
            statement = statement.where(PageVisit.user_id == user.id)
        return statement

    def period_info(self, request):
        return {'period': request.query_params.get('period', 'all'),
                'start_date': request.query_params.get('start_date'),
                'end_date': request.query_params.get('end_date')}


class VisitorStatistics(_Analytics):
    title = 'Visitor Statistics'

    async def get(self, request, session, user):
        base = self.filtered(request, user, select(PageVisit))
        rows = session.scalars(base.order_by(PageVisit.id)).unique().all()

        def group(key, label):
            counts = {}
            for row in rows:
                value = getattr(row, key)
                counts[value] = counts.get(value, 0) + 1
            return [{key: value, label: count} for value, count in counts.items()]

        pages = {}
        for row in rows:
            pages[row.path] = pages.get(row.path, 0) + 1
        most_visited = sorted(({'path': path, 'visit_count': count}
                               for path, count in pages.items()),
                              key=lambda item: (-item['visit_count'], item['path']))[:10]
        hours = {}
        for row in rows:
            hours[row.timestamp.hour] = hours.get(row.timestamp.hour, 0) + 1
        return ({
            'period_info': self.period_info(request),
            'total_visits': len(rows),
            'device_distribution': group('device_type', 'count'),
            'browser_distribution': group('browser', 'count'),
            'os_distribution': group('os', 'count'),
            'most_visited_pages': most_visited,
            'traffic_by_hour': [{'hour': hour, 'count': hours[hour]}
                                for hour in sorted(hours)],
        }, 200, {})


class ContentPerformance(_Analytics):
    title = 'Content Performance'

    async def get(self, request, session, user):
        base = self.filtered(request, user,
                             select(PageVisit).where(PageVisit.content_id.is_not(None)))
        # `time_spent` is named by the aggregate, so the query cannot even be built.
        averaged = func.avg(getattr(PageVisit, 'time_spent'))
        rows = session.execute(
            base.add_columns(averaged).group_by(PageVisit.content_id)).unique().all()
        performance = []
        for row, avg_time_spent in rows:
            performance.append({'content_id': row.content_id,
                                'total_visits': 1,
                                'unique_visitors': 1,
                                'avg_time_spent': avg_time_spent,
                                'device_breakdown': 1})
        return ({'period_info': self.period_info(request),
                 'performance': performance}, 200, {})


class ReferrerAnalysis(_Analytics):
    title = 'Referrer Analysis'

    async def get(self, request, session, user):
        base = self.filtered(request, user, select(PageVisit).where(
            PageVisit.referrer.is_not(None), PageVisit.referrer != ''))
        rows = session.scalars(base.order_by(PageVisit.id)).unique().all()
        counts = {}
        for row in rows:
            entry = counts.setdefault(row.referrer, {'visit_count': 0, 'ips': set()})
            entry['visit_count'] += 1
            entry['ips'].add(row.ip_address)
        referrers = [{'referrer': referrer, 'visit_count': entry['visit_count'],
                      'unique_visitors': len(entry['ips'])}
                     for referrer, entry in counts.items()]
        referrers.sort(key=lambda item: (-item['visit_count'], item['referrer']))
        return ({'period_info': self.period_info(request),
                 'referrers': referrers}, 200, {})
