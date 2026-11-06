"""Experimental Worker configuration; validate on the real runtime before publishing."""
import os
import logging

class WorkerExceptionFormatter(logging.Formatter):
    def format(self, record):
        message = record.getMessage()
        if record.exc_info:
            kind, error, _ = record.exc_info
            message += ' | ' + kind.__name__ + ': ' + str(error)
        return message.replace('\n', ' | ')


from workers import env

os.environ['DJANGO_DEBUG'] = 'false'
os.environ['DJANGO_SECRET_KEY'] = str(env.DJANGO_SECRET_KEY)
os.environ['DJANGO_ALLOWED_HOSTS'] = str(env.DJANGO_ALLOWED_HOSTS)

from .pilot_settings import *  # noqa: E402,F403

DATABASES = {'default': {
    'ENGINE': 'django_cf.db.backends.d1', 'CLOUDFLARE_BINDING': 'DB',
}}
MEDIA_URL = str(env.MEDIA_PUBLIC_URL).rstrip('/') + '/'
if not MEDIA_URL.startswith('https://'):
    raise ImproperlyConfigured('MEDIA_PUBLIC_URL deve usar HTTPS.')
STORAGES = {
    'default': {
        'BACKEND': 'django_cf.storage.R2Storage',
        'OPTIONS': {'binding': 'BUCKET', 'location': '', 'allow_overwrite': False},
    },
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}
# Pilot templates use inline CSS and do not need WhiteNoise. Admin assets are
# collected into public/static and served by the Worker ASSETS binding.
MIDDLEWARE = [item for item in MIDDLEWARE if not item.startswith('whitenoise.')]
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'


# Send server-side exceptions to Workers Logs, without request bodies or locals.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {'summary': {'()': WorkerExceptionFormatter}},
    'handlers': {'worker_console': {
        'class': 'logging.StreamHandler', 'stream': 'ext://sys.stdout', 'formatter': 'summary',
    }},
    'loggers': {
        'django.request': {'handlers': ['worker_console'], 'level': 'ERROR', 'propagate': False},
        'cloudpilot': {'handlers': ['worker_console'], 'level': 'ERROR', 'propagate': False},
    },
}

# Pyodide lacks hashlib.pbkdf2_hmac; retain PBKDF2-SHA256 and the source work factor.
PASSWORD_HASHERS = ['cloudpilot.hashers.WorkerPBKDF2PasswordHasher']

PORTAL_PREVIEW = True
CALENDARIO_NO_BANCO = True
DATA_DIR = BASE_DIR / 'portal_data'

