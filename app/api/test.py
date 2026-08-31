"""Test client for the API.

The tests were written against a client that took a Python payload, chose an
encoding for it, and handed back the decoded response body as ``response.data``
together with a way to sign a user in without real credentials.  Flask's test
client returns raw bytes and has no notion of an authenticated user, so that
surface is rebuilt here and the tests keep their original shape.
"""
import json
import unittest

from flask import current_app

# The client the tests were written against encoded payloads as multipart form
# data unless a test asked for something else, so a request body of
# ``{'categories': [3], 'user': [1]}`` reached the view as repeated form fields
# rather than as JSON arrays.  Several tests depend on that: they pass a list
# for a single-valued field and expect the view to read one value out of it.
DEFAULT_FORMAT = 'multipart'


def _multipart(data):
    """Render a payload the way the previous client's encoder did.

    Form data carries strings, so numbers and booleans are stringified here
    rather than being rejected by the transport.  File objects are left alone.
    """
    if not isinstance(data, dict):
        return data
    encoded = {}
    for key, value in data.items():
        if isinstance(value, (list, tuple)):
            encoded[key] = [_multipart_value(item) for item in value]
        else:
            encoded[key] = _multipart_value(value)
    return encoded


def _multipart_value(value):
    if value is None or isinstance(value, (str, bytes)):
        return value
    if hasattr(value, 'read'):
        return value
    return str(value)


class TestCase(unittest.TestCase):
    """``unittest.TestCase`` plus the one extra assertion the tests use.

    ``assertContains`` came from the previous test framework's own base class;
    it checks the status code as well as the body, so keeping it means the
    administration tests do not have to be rewritten into two assertions.
    """

    def assertContains(self, response, text, status_code=200):
        self.assertEqual(response.status_code, status_code)
        self.assertIn(str(text), response.content.decode('utf-8'))


class APIResponse:
    """Wraps a Flask response so ``.data`` is the decoded payload."""

    def __init__(self, response):
        self.response = response
        self.status_code = response.status_code
        self.headers = response.headers
        self.content = response.get_data()

    @property
    def data(self):
        if not self.content:
            return None
        try:
            return json.loads(self.content.decode('utf-8'))
        except ValueError:
            return self.content

    def __getitem__(self, header):
        return self.response.headers[header]

    def __getattr__(self, item):
        return getattr(self.response, item)


class APIClient:

    def __init__(self, app=None):
        self.app = app
        self._force_user = None
        self._force_token = None
        self._headers = {}

    @property
    def _application(self):
        return self.app or current_app._get_current_object()

    @property
    def _client(self):
        return self._application.test_client()

    def force_authenticate(self, user=None, token=None):
        self._force_user = user
        self._force_token = token

    def credentials(self, **kwargs):
        """Set headers carried by every subsequent request.

        The previous framework's client took these in WSGI form
        (``HTTP_AUTHORIZATION='Token abc'``), and the ported tests may use
        either that or a plain header name, so both are accepted.
        """
        self._headers = {
            self._header_name(key): value for key, value in kwargs.items()
        }

    @staticmethod
    def _header_name(key):
        if key.startswith('HTTP_'):
            key = key[len('HTTP_'):]
        return key.replace('_', '-').title()

    def _environ(self):
        environ = {}
        if self._force_user is not None or self._force_token is not None:
            environ['app.force_auth_user'] = self._force_user
            environ['app.force_auth_token'] = self._force_token
        return environ

    def _request(self, method, path, data=None, format=DEFAULT_FORMAT,
                 **kwargs):
        # Headers set by ``credentials()`` apply to every request; anything
        # passed to the call itself wins over them.
        headers = dict(self._headers)
        headers.update(kwargs.pop('headers', None) or {})
        if data is None:
            body = {}
        elif format == 'json':
            body = {'json': data}
        else:
            body = {'data': _multipart(data)}
        client = self._client
        response = getattr(client, method)(
            path, headers=headers, environ_base=self._environ(),
            **body, **kwargs
        )
        return APIResponse(response)

    def get(self, path, data=None, **kwargs):
        if data:
            kwargs['query_string'] = data
        return self._request('get', path, **kwargs)

    def post(self, path, data=None, format=DEFAULT_FORMAT, **kwargs):
        return self._request('post', path, data, format, **kwargs)

    def put(self, path, data=None, format=DEFAULT_FORMAT, **kwargs):
        return self._request('put', path, data, format, **kwargs)

    def patch(self, path, data=None, format=DEFAULT_FORMAT, **kwargs):
        return self._request('patch', path, data, format, **kwargs)

    def delete(self, path, data=None, format=DEFAULT_FORMAT, **kwargs):
        return self._request('delete', path, data, format, **kwargs)


class Client(APIClient):
    """Session-based client, used by the administration tests."""

    def force_login(self, user):
        client = self._application.test_client()
        with client.session_transaction() as session:
            session['_user_id'] = str(user.id)
            session['_fresh'] = True
        self._session_client = client

    @property
    def _client(self):
        return getattr(self, '_session_client', None) or super()._client
