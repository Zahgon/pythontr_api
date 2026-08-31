"""A response the views can build before the view layer knows about headers.

Views return ``Response(data, status=...)`` and the dispatcher turns it into a
real Flask response once the ``Allow`` header and the JSON encoding settings
are known.
"""
from flask import json

# The renderer this replaces emitted compact JSON and left non-ASCII
# characters untouched, so the Turkish error strings travel as UTF-8 rather
# than as \u escapes.  Both are visible on the wire, hence the explicit
# arguments instead of the encoder defaults.
SEPARATORS = (',', ':')


class Response:

    def __init__(self, data=None, status=200, headers=None,
                 content_type=None):
        self.data = data
        self.status = status
        self.headers = dict(headers or {})
        self.content_type = content_type

    def to_flask_response(self):
        from flask import make_response

        if self.status == 204 or self.data is None:
            response = make_response('', self.status)
            response.headers.pop('Content-Type', None)
        else:
            body = json.dumps(
                self.data, ensure_ascii=False, separators=SEPARATORS
            )
            response = make_response(body, self.status)
            response.headers['Content-Type'] = (
                self.content_type or 'application/json'
            )
        for key, value in self.headers.items():
            response.headers[key] = value
        return response
