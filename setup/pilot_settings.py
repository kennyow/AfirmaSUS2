"""Isolated native-Python pilot. Never points at the source project's database."""
from .settings import *  # noqa: F403

INSTALLED_APPS = [*INSTALLED_APPS, 'cloudpilot']
ROOT_URLCONF = 'setup.pilot_urls'
MIDDLEWARE = ['cloudpilot.middleware.UploadSizeMiddleware', *[
    item for item in MIDDLEWARE if not item.startswith('whitenoise.')
]]
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/arquivos/'
LOGOUT_REDIRECT_URL = '/'
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'pilot.sqlite3'}}
MEDIA_ROOT = BASE_DIR / 'pilot-media'
STATIC_ROOT = BASE_DIR / 'public' / 'static'
FILE_UPLOAD_MAX_MEMORY_SIZE = 12 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 512 * 1024
DATA_UPLOAD_MAX_NUMBER_FILES = 1

MIDDLEWARE += ['cloudpilot.portal_preview.PortalPreviewMiddleware']
TEMPLATES[0]['OPTIONS']['context_processors'] += ['cloudpilot.portal_preview.context']

