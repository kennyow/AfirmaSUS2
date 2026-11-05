"""Cloudflare entrypoint, based on the official Django/D1 example."""
import os

from django_cf import DjangoCF
from workers import WorkerEntrypoint

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'setup.cloudflare_settings')


class Default(DjangoCF, WorkerEntrypoint):
    def get_app(self):
        from django.core.wsgi import get_wsgi_application

        return get_wsgi_application()
