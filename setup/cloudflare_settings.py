"""Experimental Worker configuration; validate on the real runtime before publishing."""
import os

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

