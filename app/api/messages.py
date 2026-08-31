"""Turkish user-facing strings for the HTTP layer.

The API has always answered in Turkish: the previous framework shipped its own
Turkish catalogue and the project selected it with ``LANGUAGE_CODE = 'tr'``.
Those strings are part of the public contract of this service -- clients match
on them -- so they are reproduced here verbatim rather than re-translated.
"""

NOT_AUTHENTICATED = 'Giriş bilgileri verilmedi.'
AUTHENTICATION_FAILED = 'Giriş bilgileri hatalı.'
INVALID_TOKEN = 'Geçersiz simge.'
INVALID_TOKEN_HEADER_NO_CREDENTIALS = (
    'Geçersiz token başlığı. Kimlik bilgileri eksik.'
)
INVALID_TOKEN_HEADER_SPACES = (
    "Geçersiz token başlığı. Token'da boşluk olmamalı."
)
INVALID_TOKEN_HEADER_CHARACTERS = (
    'Geçersiz token başlığı. Token geçersiz karakter içermemeli.'
)
USER_INACTIVE_OR_DELETED = 'Kullanıcı aktif değil ya da silinmiş'
PERMISSION_DENIED = 'Bu işlemi yapmak için izniniz bulunmuyor.'
NOT_FOUND = 'Bulunamadı.'
METHOD_NOT_ALLOWED = '"{method}" metoduna izin verilmiyor.'
PARSE_ERROR = 'Bozuk istek.'
UNSUPPORTED_MEDIA_TYPE = 'İstekte desteklenmeyen medya tipi: "{media_type}".'
SERVER_ERROR = 'Sunucu hatası oluştu.'
INVALID_PAGE = 'Geçersiz sayfa.'

REQUIRED = 'Bu alan zorunlu.'
NULL = 'Bu alan boş bırakılmamalı.'
BLANK = 'Bu alan boş bırakılmamalı.'
INVALID_INPUT = 'Invalid input.'
INVALID_STRING = 'Not a valid string.'
INVALID_DATA = 'Geçersiz veri. Bir sözlük bekleniyor, ama var {datatype}.'
INVALID_EMAIL = 'Geçerli bir e-posta adresi girin.'
INVALID_BOOLEAN = '"{input}" is not a valid boolean.'
INVALID_INTEGER = 'Geçerli bir tam sayı girin.'
INVALID_DATETIME = (
    'Datetime alanı yanlış biçimde. {format} biçimlerinden birini kullanın.'
)
NO_FILE = 'Hiçbir dosya verilmedi.'
MIN_LENGTH = (
    'Bu alanın en az {min_length} karakter barındırdığından emin olun.'
)
MAX_LENGTH = (
    'Bu alanın {max_length} karakterden fazla karakter barındırmadığından '
    'emin olun.'
)
UNIQUE = 'Bu {field} alanına sahip {model} zaten mevcut.'
DOES_NOT_EXIST = 'Geçersiz pk "{pk_value}" - obje bulunamadı.'
INCORRECT_TYPE = 'Hatalı tip. Pk değeri beklenirken, alınan {data_type}.'

# app/authentication.py
COOKIE_TOKEN_INVALID_FORMAT = 'Geçersiz token formatı.'
COOKIE_TOKEN_INVALID = 'Geçersiz token.'
COOKIE_USER_INACTIVE = 'Kullanıcı hesabı aktif değil.'

# recipe/serializers/serializer_article.py
ONLY_ADMIN_CAN_APPROVE = 'Onay durumunu sadece yöneticiler değiştirebilir.'

# recipe/permissions.py
NOT_OWNER = 'You must be the owner of this object.'
