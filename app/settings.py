"""Settings for the app project.

A plain module, read with ``from app import settings``. The names and the environment
variables they come from are unchanged from the Django configuration this replaced.
"""

import os
import sys

from dotenv import load_dotenv

from app.i18n import gettext_lazy as _


load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SECRET_KEY = 's#kkb7z3ste9!7fo#__7jq*ey5+ro_$ho83b=4@ziw&!9=_h86'

DEBUG = os.environ.get('DEBUG', '').lower() == 'true'

ALLOWED_HOSTS = os.environ.get('ALLOW_HOST').split(',')

LANGUAGE_CODE = 'tr'

LANGUAGES = [
    ('tr', _('turkish')),
    ('en', _('english')),
]

LOCALE_PATHS = [
    os.path.join(BASE_DIR, 'locale'),
]

API = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'app.authentication.CookieTokenAuthentication',
        'app.authentication.TokenAuthentication',  # Geriye dönük uyumluluk için
    ],
}

TOKEN_EXPIRED_AFTER_SECONDS = 86400

if 'test' not in sys.argv:
    API['DEFAULT_PAGINATION_CLASS'] = 'core.pagination.CustomPagination'
    API['PAGE_SIZE'] = 27

RECAPTCHA_URL = 'https://www.google.com/recaptcha/api/siteverify'
RECAPTCHA_SITE_KEY = os.environ.get('RECAPTCHA_SITE_KEY')
RECAPTCHA_SECRET_KEY = os.environ.get('RECAPTCHA_SECRET_KEY')

MIDDLEWARE = [
    'app.middleware.SecurityMiddleware',
    'app.middleware.CommonMiddleware',
    'app.middleware.XFrameOptionsMiddleware',
    'app.middleware.LocaleMiddleware',
]

DATABASES = {
    'default': {
        'ENGINE': os.environ.get('DB_ENGINE'),
        'HOST': os.environ.get('DB_HOST'),
        'NAME': os.environ.get('DB_NAME'),
        'USER': os.environ.get('DB_USER'),
        'PASSWORD': os.environ.get('DB_PASS'),
        'PORT': os.environ.get('DB_PORT'),
    }
}

SITE_URL = os.environ.get('SITE_URL', 'http://localhost:8000')

EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'app.mail.backends.smtp.EmailBackend')
EMAIL_HOST = os.environ.get('EMAIL_HOST')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 25))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', '').lower() == 'true'
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL')

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'app.validators.UserAttributeSimilarityValidator'},
    {'NAME': 'app.validators.MinimumLengthValidator'},
    {'NAME': 'app.validators.CommonPasswordValidator'},
    {'NAME': 'app.validators.NumericPasswordValidator'},
]

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

STATIC_URL = '/static/'

STATICFILES_DIRS = (
    os.path.join(BASE_DIR, 'static'),
)

AVATAR_ROOT = 'static/avatar/'
ARTICLE_ROOT = 'static/article/'
IMAGE_ROOT = 'static/img/'

APLICATION_NAME = 'app'
AUTH_USER_MODEL = 'core.User'

APPEND_SLASH = True
X_FRAME_OPTIONS = 'DENY'

CSRF_TRUSTED_ORIGINS = ['https://*.pythontr.com']
