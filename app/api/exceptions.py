"""Exception hierarchy for the HTTP layer.

Every exception carries the status code and the JSON body that the endpoint
answered with before the migration, in the language negotiated for the request
that raised it.
"""

from flask import jsonify

from app.api import messages


class APIException(Exception):
    """Base class for every error the API renders as JSON."""

    status_code = 500
    default_detail = messages.SERVER_ERROR

    def __init__(self, detail=None, status_code=None):
        detail = self.default_detail if detail is None else detail
        if isinstance(detail, str):
            detail = messages.localize(detail)
        super().__init__(detail)
        self.detail = detail
        if status_code is not None:
            self.status_code = status_code

    def get_body(self):
        return {'detail': self.detail}

    def get_headers(self):
        auth_header = getattr(self, 'auth_header', None)
        if auth_header:
            return {'WWW-Authenticate': auth_header}
        return {}


class ParseError(APIException):
    status_code = 400
    default_detail = messages.PARSE_ERROR


class UnsupportedMediaType(APIException):
    status_code = 415

    def __init__(self, media_type, detail=None):
        if detail is None:
            detail = messages.localize(messages.UNSUPPORTED_MEDIA_TYPE).format(
                media_type=media_type,
            )
        super().__init__(detail)


class ValidationError(APIException):
    """Field level validation failure.

    ``detail`` is a mapping of field name to a list of messages, exactly the
    shape the serializers produced before.
    """

    status_code = 400
    default_detail = messages.INVALID_INPUT

    def __init__(self, detail=None, status_code=None):
        if detail is None:
            detail = {'non_field_errors': [messages.localize(
                self.default_detail)]}
        elif not isinstance(detail, (dict, list)):
            detail = {'non_field_errors': [messages.localize(detail)]}
        super().__init__(detail, status_code)

    def get_body(self):
        return self.detail


class NotAuthenticated(APIException):
    status_code = 401
    default_detail = messages.NOT_AUTHENTICATED


class AuthenticationFailed(APIException):
    status_code = 401
    default_detail = messages.AUTHENTICATION_FAILED


class PermissionDenied(APIException):
    status_code = 403
    default_detail = messages.PERMISSION_DENIED


class NotFound(APIException):
    status_code = 404
    default_detail = messages.NOT_FOUND


class NotAcceptable(APIException):
    status_code = 406
    default_detail = messages.NOT_ACCEPTABLE


class MethodNotAllowed(APIException):
    status_code = 405
    default_detail = messages.METHOD_NOT_ALLOWED

    def __init__(self, method, detail=None, status_code=None):
        if detail is None:
            detail = messages.localize(messages.METHOD_NOT_ALLOWED).format(
                method=method)
        super().__init__(detail, status_code)


def render_api_exception(exc):
    """Turn an :class:`APIException` into a Flask response."""
    response = jsonify(exc.get_body())
    response.status_code = exc.status_code
    response.headers.extend(exc.get_headers())
    return response
