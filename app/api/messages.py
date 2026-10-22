"""User-facing strings for the HTTP layer, in both languages the API speaks.

The API has always answered in the language ``Accept-Language`` negotiates:
the previous framework translated its messages through the active language,
which its locale middleware selected per request (``tr`` unless the client
asks for ``en``), with its own Turkish catalogue behind ``LANGUAGE_CODE =
'tr'``.  Those strings are part of the public contract of this service --
clients match on them -- so both renderings are reproduced here verbatim
rather than re-translated.

Each catalogue entry is a :class:`Message`: a ``str`` holding the Turkish text
(so comparing against the Turkish wording keeps working) that also carries
the English one.  :func:`localize` picks the rendering for the current
request; it has to run before ``str.format``, because formatting returns a
plain string that no longer knows its other language.  Strings the previous
catalogue never translated are plain ``str`` and read the same in both.
"""


class Message(str):
    """A catalogue entry: the Turkish text, with the English one attached."""

    def __new__(cls, turkish, english):
        message = super().__new__(cls, turkish)
        message.en = english
        return message


def current_language():
    """The language negotiated for the request being handled, else ``tr``."""
    from flask import has_request_context

    if not has_request_context():
        return 'tr'
    from app import select_locale

    return str(select_locale())


def localize(message):
    """Render ``message`` in the negotiated language."""
    if isinstance(message, Message) and current_language() == 'en':
        return message.en
    return str(message)


NOT_AUTHENTICATED = Message(
    'Giriş bilgileri verilmedi.',
    'Authentication credentials were not provided.',
)
AUTHENTICATION_FAILED = Message(
    'Giriş bilgileri hatalı.', 'Incorrect authentication credentials.'
)
INVALID_TOKEN = Message('Geçersiz simge.', 'Invalid token.')
INVALID_TOKEN_HEADER_NO_CREDENTIALS = Message(
    'Geçersiz token başlığı. Kimlik bilgileri eksik.',
    'Invalid token header. No credentials provided.',
)
INVALID_TOKEN_HEADER_SPACES = Message(
    "Geçersiz token başlığı. Token'da boşluk olmamalı.",
    'Invalid token header. Token string should not contain spaces.',
)
INVALID_TOKEN_HEADER_CHARACTERS = Message(
    'Geçersiz token başlığı. Token geçersiz karakter içermemeli.',
    'Invalid token header. Token string should not contain invalid '
    'characters.',
)
USER_INACTIVE_OR_DELETED = Message(
    'Kullanıcı aktif değil ya da silinmiş', 'User inactive or deleted.'
)
PERMISSION_DENIED = Message(
    'Bu işlemi yapmak için izniniz bulunmuyor.',
    'You do not have permission to perform this action.',
)
NOT_FOUND = Message('Bulunamadı.', 'Not found.')
METHOD_NOT_ALLOWED = Message(
    '"{method}" metoduna izin verilmiyor.', 'Method "{method}" not allowed.'
)
PARSE_ERROR = Message('Bozuk istek.', 'Malformed request.')
UNSUPPORTED_MEDIA_TYPE = Message(
    'İstekte desteklenmeyen medya tipi: "{media_type}".',
    'Unsupported media type "{media_type}" in request.',
)
SERVER_ERROR = Message('Sunucu hatası oluştu.', 'A server error occurred.')
INVALID_PAGE = Message('Geçersiz sayfa.', 'Invalid page.')
NOT_ACCEPTABLE = Message(
    'İsteğe ait Accept başlık bilgisi yanıt verilecek başlık bilgileri '
    'arasında değil.',
    'Could not satisfy the request Accept header.',
)

REQUIRED = Message('Bu alan zorunlu.', 'This field is required.')
NULL = Message('Bu alan boş bırakılmamalı.', 'This field may not be null.')
BLANK = Message('Bu alan boş bırakılmamalı.', 'This field may not be blank.')
INVALID_INPUT = 'Invalid input.'
INVALID_STRING = 'Not a valid string.'
INVALID_DATA = Message(
    'Geçersiz veri. Bir sözlük bekleniyor, ama var {datatype}.',
    'Invalid data. Expected a dictionary, but got {datatype}.',
)
INVALID_EMAIL = Message(
    'Geçerli bir e-posta adresi girin.', 'Enter a valid email address.'
)
# The Turkish catalogue never translated this one.
INVALID_BOOLEAN = 'Must be a valid boolean.'
INVALID_INTEGER = Message(
    'Geçerli bir tam sayı girin.', 'A valid integer is required.'
)
INVALID_DATETIME = Message(
    'Datetime alanı yanlış biçimde. {format} biçimlerinden birini kullanın.',
    'Datetime has wrong format. Use one of these formats instead: {format}.',
)
NO_FILE = Message('Hiçbir dosya verilmedi.', 'No file was submitted.')
MIN_LENGTH = Message(
    'Bu alanın en az {min_length} karakter barındırdığından emin olun.',
    'Ensure this field has at least {min_length} characters.',
)
MAX_LENGTH = Message(
    'Bu alanın {max_length} karakterden fazla karakter barındırmadığından '
    'emin olun.',
    'Ensure this field has no more than {max_length} characters.',
)
UNIQUE = Message(
    'Bu {field} alanına sahip {model} zaten mevcut.',
    '{model} with this {field} already exists.',
)
DOES_NOT_EXIST = Message(
    'Geçersiz pk "{pk_value}" - obje bulunamadı.',
    'Invalid pk "{pk_value}" - object does not exist.',
)
INCORRECT_TYPE = Message(
    'Hatalı tip. Pk değeri beklenirken, alınan {data_type}.',
    'Incorrect type. Expected pk value, received {data_type}.',
)

# app/authentication.py
COOKIE_TOKEN_INVALID_FORMAT = 'Geçersiz token formatı.'
COOKIE_TOKEN_INVALID = 'Geçersiz token.'
COOKIE_USER_INACTIVE = 'Kullanıcı hesabı aktif değil.'

# recipe/serializers/serializer_article.py
ONLY_ADMIN_CAN_APPROVE = 'Onay durumunu sadece yöneticiler değiştirebilir.'

# recipe/permissions.py
NOT_OWNER = 'You must be the owner of this object.'
